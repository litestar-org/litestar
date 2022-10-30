from typing import Optional

from sqlalchemy import Column, Float, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base

from starlite import DTOFactory, Starlite, get, post
from starlite.plugins.sql_alchemy import SQLAlchemyConfig, SQLAlchemyPlugin

Base = declarative_base()

sqlalchemy_config = SQLAlchemyConfig(connection_string="sqlite+aiosqlite://", dependency_key="async_session")
sqlalchemy_plugin = SQLAlchemyPlugin(config=sqlalchemy_config)
dto_factory = DTOFactory(plugins=[sqlalchemy_plugin])


class Company(Base):  # type: ignore
    __tablename__ = "company"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    worth = Column(Float)


CreateCompanyDTO = dto_factory("CreateCompanyDTO", Company, exclude=["id"])


async def on_startup() -> None:
    """Initialize the database."""
    async with sqlalchemy_config.engine.begin() as conn:  # type: ignore
        await conn.run_sync(Base.metadata.create_all)  # pyright: ignore


@post(path="/companies")
async def create_company(
    data: CreateCompanyDTO,  # type: ignore
    async_session: AsyncSession,
) -> Company:
    company = Company(**data.dict())
    async_session.add(company)
    return await async_session.commit()


@get(path="/companies/{company_id:int}")
async def get_company(company_id: str, async_session: AsyncSession) -> Optional[Company]:
    company = await async_session.scalar(select(Company).where(Company.id == company_id))
    return company


app = Starlite(
    route_handlers=[create_company, get_company],
    on_startup=[on_startup],
    plugins=[sqlalchemy_plugin],
)
