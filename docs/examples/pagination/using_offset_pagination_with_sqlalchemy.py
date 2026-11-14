import dataclasses

from advanced_alchemy.extensions.litestar import SQLAlchemyAsyncConfig, SQLAlchemyPlugin
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from litestar import Litestar, get
from litestar.di import NamedDependency, Provide
from litestar.pagination import AbstractAsyncOffsetPaginator, OffsetPagination
from litestar.params import FromQuery


class Base(DeclarativeBase): ...


class PersonModel(Base):
    __tablename__ = "person"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]


@dataclasses.dataclass
class Person:
    id: int
    name: str


# the paginator implements the same two methods as the in-memory example, but each one is
# now a coroutine that queries the database through an injected SQLAlchemy session.


class PersonOffsetPaginator(AbstractAsyncOffsetPaginator[Person]):
    def __init__(self, db_session: NamedDependency[AsyncSession]) -> None:
        self.db_session = db_session

    async def get_total(self) -> int:
        total = await self.db_session.scalar(select(func.count()).select_from(PersonModel))
        return total or 0

    async def get_items(self, limit: int, offset: int) -> list[Person]:
        people = await self.db_session.scalars(select(PersonModel).limit(limit).offset(offset))
        return [Person(id=person.id, name=person.name) for person in people]


# the paginator is provided as a dependency so that Litestar injects the request-scoped
# session into it. A class is always a synchronous callable, hence 'sync_to_thread=False'.
@get("/people", dependencies={"paginator": Provide(PersonOffsetPaginator, sync_to_thread=False)})
async def people_handler(
    paginator: NamedDependency[PersonOffsetPaginator], limit: FromQuery[int], offset: FromQuery[int]
) -> OffsetPagination[Person]:
    return await paginator(limit=limit, offset=offset)


sqlalchemy_config = SQLAlchemyAsyncConfig(
    connection_string="sqlite+aiosqlite:///:memory:",
    metadata=Base.metadata,
    create_all=True,
)


async def on_startup() -> None:
    """Populate the in-memory database so the example returns data."""
    async with sqlalchemy_config.create_session_maker()() as db_session:
        db_session.add_all([PersonModel(name=f"Person {i}") for i in range(1, 51)])
        await db_session.commit()


app = Litestar(
    route_handlers=[people_handler],
    plugins=[SQLAlchemyPlugin(config=sqlalchemy_config)],
    on_startup=[on_startup],
)
