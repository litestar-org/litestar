from __future__ import annotations
from uuid import uuid4
import anyio

from sqlalchemy import bindparam
from sqlalchemy import Column
from sqlalchemy import create_engine
from sqlalchemy import insert
from sqlalchemy import String
from sqlalchemy.orm import Session
import argparse
import cProfile
import gc
import os
import pstats
import re
import sys
import time

from starlite.contrib.sqlalchemy.base import Base
from starlite.contrib.sqlalchemy.repository import SQLAlchemyRepository
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker


class Profiler:
    tests = []

    _setup = None
    _setup_once = None
    name = None
    num = 0

    def __init__(self, options):
        self.test = options.test
        self.dburl = options.dburl
        self.profile = options.profile
        self.dump = options.dump
        self.raw = options.raw
        self.callers = options.callers
        self.num = options.num
        self.echo = options.echo
        self.sort = options.sort
        self.gc = options.gc
        self.stats = []

    @classmethod
    def init(cls, name, num):
        cls.name = name
        cls.num = num

    @classmethod
    def profile(cls, fn):
        if cls.name is None:
            raise ValueError("Need to call Profile.init(<suitename>, <default_num>) first.")
        cls.tests.append(fn)
        return fn

    @classmethod
    def setup(cls, fn):
        if cls._setup is not None:
            raise ValueError("setup function already set to %s" % cls._setup)
        cls._setup = staticmethod(fn)
        return fn

    @classmethod
    def setup_once(cls, fn):
        if cls._setup_once is not None:
            raise ValueError("setup_once function already set to %s" % cls._setup_once)
        cls._setup_once = staticmethod(fn)
        return fn

    def run(self):
        if self.test:
            tests = [fn for fn in self.tests if fn.__name__ in self.test]
            if not tests:
                raise ValueError("No such test(s): %s" % self.test)
        else:
            tests = self.tests

        if self._setup_once:
            print("Running setup once...")
            self._setup_once(self.dburl, self.echo, self.num)
        print("Tests to run: %s" % ", ".join([t.__name__ for t in tests]))
        for test in tests:
            self._run_test(test)
            self.stats[-1].report()

    def _run_with_profile(self, fn, sort):
        pr = cProfile.Profile()
        pr.enable()
        try:
            result = fn(self.num)
        finally:
            pr.disable()

        stats = pstats.Stats(pr)

        self.stats.append(TestResult(self, fn, stats=stats, sort=sort))
        return result

    def _run_with_time(self, fn):
        now = time.time()
        try:
            return fn(self.num)
        finally:
            total = time.time() - now
            self.stats.append(TestResult(self, fn, total_time=total))

    def _run_test(self, fn):
        if self._setup:
            self._setup(self.dburl, self.echo, self.num)
        if self.gc:
            gc.set_debug(gc.DEBUG_STATS)
        if self.profile or self.dump:
            self._run_with_profile(fn, self.sort)
        else:
            self._run_with_time(fn)
        if self.gc:
            gc.set_debug(0)

    @classmethod
    def main(cls):

        parser = argparse.ArgumentParser("python -m examples.performance")

        if cls.name is None:
            parser.add_argument("name", choices=cls._suite_names(), help="suite to run")

            if len(sys.argv) > 1:
                potential_name = sys.argv[1]
                try:
                    __import__(__name__ + "." + potential_name)
                except ImportError:
                    pass

        parser.add_argument("--test", nargs="+", type=str, help="run specific test(s)")

        parser.add_argument(
            "--dburl",
            type=str,
            default="sqlite:///profile.db",
            help="database URL, default sqlite:///profile.db",
        )
        parser.add_argument(
            "--num",
            type=int,
            default=cls.num,
            help="Number of iterations/items/etc for tests; " "default is %d module-specific" % cls.num,
        )
        parser.add_argument(
            "--profile",
            action="store_true",
            help="run profiling and dump call counts",
        )
        parser.add_argument(
            "--sort",
            type=str,
            default="cumulative",
            help="profiling sort, defaults to cumulative",
        )
        parser.add_argument(
            "--dump",
            action="store_true",
            help="dump full call profile (implies --profile)",
        )
        parser.add_argument(
            "--raw",
            type=str,
            help="dump raw profile data to file (implies --profile)",
        )
        parser.add_argument(
            "--callers",
            action="store_true",
            help="print callers as well (implies --dump)",
        )
        parser.add_argument("--gc", action="store_true", help="turn on GC debug stats")
        parser.add_argument("--echo", action="store_true", help="Echo SQL output")
        args = parser.parse_args()

        args.dump = args.dump or args.callers
        args.profile = args.profile or args.dump or args.raw

        if cls.name is None:
            __import__(__name__ + "." + args.name)

        Profiler(args).run()

    @classmethod
    def _suite_names(cls):
        suites = []
        for file_ in os.listdir(os.path.dirname(__file__)):
            match = re.match(r"^([a-z].*).py$", file_)
            if match:
                suites.append(match.group(1))
        return suites


class TestResult:
    def __init__(self, profile, test, stats=None, total_time=None, sort="cumulative"):
        self.profile = profile
        self.test = test
        self.stats = stats
        self.total_time = total_time
        self.sort = sort

    def report(self):
        print(self._summary())
        if self.profile.profile:
            self.report_stats()

    def _summary(self):
        summary = "%s : %s (%d iterations)" % (
            self.test.__name__,
            self.test.__doc__,
            self.profile.num,
        )
        if self.total_time:
            summary += "; total time %f sec" % self.total_time
        if self.stats:
            summary += "; total fn calls %d" % self.stats.total_calls
        return summary

    def report_stats(self):
        if self.profile.dump:
            self._dump(self.sort)
        elif self.profile.raw:
            self._dump_raw()

    def _dump(self, sort):
        self.stats.sort_stats(*re.split(r"[ ,]", self.sort))
        self.stats.print_stats()
        if self.profile.callers:
            self.stats.print_callers()

    def _dump_raw(self):
        self.stats.dump_stats(self.profile.raw)


class Customer(Base):
    __tablename__ = "customer"
    name = Column(String(255))
    description = Column(String(255))


class CustomerRepository(SQLAlchemyRepository[Customer]):
    """Customer repository."""

    model_type = Customer


Profiler.init("bulk_inserts", num=100000)


@Profiler.setup
def setup_database(dburl, echo, num):
    global engine
    global async_engine
    engine = create_engine(dburl, echo=echo)
    async_engine = create_async_engine("sqlite+aiosqlite:///profile.async.db", echo=echo)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    async def _setup_db():
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    anyio.run(_setup_db)


@Profiler.profile
def test_flush_no_pk(n):
    """INSERT statements via the ORM (batched with RETURNING if available),   fetching generated row id"""
    session = Session(bind=engine)
    for chunk in range(0, n, 1000):
        session.add_all(
            [
                Customer(
                    name="customer name %d" % i,
                    description="customer description %d" % i,
                )
                for i in range(chunk, chunk + 1000)
            ]
        )
        session.flush()
    session.commit()


@Profiler.profile
def test_async_get_many_no_pk(n):
    """Async Get Many INSERT statements via the ORM (batched with RETURNING if available),   fetching generated row id"""
    session = async_sessionmaker(bind=async_engine)()
    repo = CustomerRepository(session=session)
    data_to_insert = []
    for chunk in range(0, n, 1000):
        data_to_insert.extend(
            [
                Customer(
                    name="customer name %d" % i,
                    description="customer description %d" % i,
                )
                for i in range(chunk, chunk + 1000)
            ]
        )

    async def _insert(repo: CustomerRepository, data_to_insert: list[Customer]) -> None:
        _ = await repo.add_many(data_to_insert)
        await repo.session.commit()

    _ = anyio.run(_insert, repo, data_to_insert)


@Profiler.profile
def test_flush_pk_given(n):
    """Batched INSERT statements via the ORM, PKs already defined"""
    session = Session(bind=engine)
    for chunk in range(0, n, 1000):
        session.add_all(
            [
                Customer(
                    id=uuid4(),
                    name="customer name %d" % i,
                    description="customer description %d" % i,
                )
                for i in range(chunk, chunk + 1000)
            ]
        )
        session.flush()
    session.commit()


@Profiler.profile
def test_orm_bulk_insert(n):
    """Batched INSERT statements via the ORM in "bulk", not returning rows"""
    session = Session(bind=engine)
    session.execute(
        insert(Customer),
        [
            {
                "name": "customer name %d" % i,
                "description": "customer description %d" % i,
            }
            for i in range(n)
        ],
    )
    session.commit()


@Profiler.profile
def test_orm_insert_returning(n):
    """Batched INSERT statements via the ORM in "bulk", returning new Customer   objects"""
    session = Session(bind=engine)

    customer_result = session.scalars(
        insert(Customer).returning(Customer),
        [
            {
                "name": "customer name %d" % i,
                "description": "customer description %d" % i,
            }
            for i in range(n)
        ],
    )

    # this step is where the rows actually become objects
    customers = customer_result.all()  # noqa: F841

    session.commit()


@Profiler.profile
def test_core_insert(n):
    """A single Core INSERT construct inserting mappings in bulk."""
    with engine.begin() as conn:
        conn.execute(
            Customer.__table__.insert(),
            [
                {
                    "name": "customer name %d" % i,
                    "description": "customer description %d" % i,
                }
                for i in range(n)
            ],
        )


@Profiler.profile
def test_dbapi_raw(n):
    """The DBAPI's API inserting rows in bulk."""

    conn = engine.pool._creator()
    cursor = conn.cursor()
    compiled = (
        Customer.__table__.insert()
        .values(name=bindparam("name"), description=bindparam("description"))
        .compile(dialect=engine.dialect)
    )

    if compiled.positional:
        args = (("customer name %d" % i, "customer description %d" % i) for i in range(n))
    else:
        args = (
            {
                "name": "customer name %d" % i,
                "description": "customer description %d" % i,
            }
            for i in range(n)
        )

    cursor.executemany(str(compiled), list(args))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    Profiler.main()
