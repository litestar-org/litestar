from typing import Optional

from sqlalchemy import Column, Float, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, declarative_base

from starlite import Starlite, get, post
from starlite.contrib.sqlalchemy_1.config import SQLAlchemyConfig
from starlite.contrib.sqlalchemy_1.plugin import SQLAlchemyPlugin
from starlite.dto import DTOFactory
from starlite.exceptions import HTTPException
from starlite.status_codes import HTTP_404_NOT_FOUND

Base = declarative_base()

sqlalchemy_config = SQLAlchemyConfig(
    connection_string="sqlite+aiosqlite:///test.sqlite", dependency_key="async_session"
)
sqlalchemy_plugin = SQLAlchemyPlugin(config=sqlalchemy_config)
dto_factory = DTOFactory(plugins=[sqlalchemy_plugin])


class Company(Base):  # pyright: ignore
    __tablename__ = "company"
    id: Mapped[int] = Column(Integer, primary_key=True)
    name: Mapped[str] = Column(String)
    worth: Mapped[float] = Column(Float)


CreateCompanyDTO = dto_factory("CreateCompanyDTO", Company, exclude=["id"])


async def on_startup() -> None:
    """Initialize the database."""
    async with sqlalchemy_config.engine.begin() as conn:  # type: ignore
        await conn.run_sync(Base.metadata.create_all)  # pyright: ignore


@post(path="/companies")
async def create_company(
    data: CreateCompanyDTO,  # type: ignore[valid-type]
    async_session: AsyncSession,
) -> Company:
    """Create a new company and return it."""
    company: Company = data.to_model_instance()  # type: ignore[attr-defined]
    async_session.add(company)
    await async_session.commit()
    return company


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


app = Starlite(
    route_handlers=[create_company, get_company],
    on_startup=[on_startup],
    plugins=[sqlalchemy_plugin],
)
