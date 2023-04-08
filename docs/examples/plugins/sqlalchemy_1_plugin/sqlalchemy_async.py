from typing import Optional

from sqlalchemy import Column, Float, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, declarative_base

from litestar import Litestar, get, post
from litestar.contrib.sqlalchemy_1.config import SQLAlchemyConfig
from litestar.contrib.sqlalchemy_1.plugin import SQLAlchemyPlugin
from litestar.exceptions import HTTPException
from litestar.status_codes import HTTP_404_NOT_FOUND

Base = declarative_base()

sqlalchemy_config = SQLAlchemyConfig(
    connection_string="sqlite+aiosqlite:///test.sqlite", dependency_key="async_session"
)
sqlalchemy_plugin = SQLAlchemyPlugin(config=sqlalchemy_config)


class Company(Base):  # pyright: ignore
    __tablename__ = "company"
    id: Mapped[int] = Column(Integer, primary_key=True)
    name: Mapped[str] = Column(String)
    worth: Mapped[float] = Column(Float)


async def on_startup() -> None:
    """Initialize the database."""
    async with sqlalchemy_config.engine.begin() as conn:  # type: ignore
        await conn.run_sync(Base.metadata.create_all)  # pyright: ignore


@post(path="/companies")
async def create_company(data: Company, async_session: AsyncSession) -> Company:
    """Create a new company and return it."""
    async_session.add(data)
    await async_session.commit()
    return data


@get(path="/companies/{company_id:int}")
async def get_company(company_id: int, async_session: AsyncSession) -> Company:
    """Get a company by its ID and return it.

    If a company with that ID does not exist, return a 404 response
    """
    result = await async_session.scalars(select(Company).where(Company.id == company_id))
    company: Optional[Company] = result.one_or_none()
    if not company:
        raise HTTPException(detail=f"Company with ID {company_id} not found", status_code=HTTP_404_NOT_FOUND)
    return company


app = Litestar(
    route_handlers=[create_company, get_company],
    on_startup=[on_startup],
    plugins=[sqlalchemy_plugin],
)
