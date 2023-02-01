from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import Column, Integer, String, select
from sqlalchemy.orm import Mapped, declarative_base
from sqlalchemy.ext.asyncio import AsyncSession

from starlite import Controller, DTOFactory, HTTPException, Starlite, get
from starlite.dto import DTO
from starlite.plugins.sql_alchemy import SQLAlchemyConfig, SQLAlchemyPlugin
from starlite.status_codes import HTTP_404_NOT_FOUND

if TYPE_CHECKING:
    from sqlalchemy.engine.result import ScalarResult

Base = declarative_base()


class Company(Base):  # pyright: ignore
    """SQlAlchemy model of a table 'company'."""

    __tablename__ = "company"
    id: Mapped[int] = Column(Integer, primary_key=True)
    name: Mapped[str] = Column(String)


class CompanyController(Controller):
    """APIs that are to be tested."""

    path: str = "/companies"

    @get(path="/{company_id:int}")
    async def get_company_by_id(self, company_id: int, async_session: AsyncSession) -> DTO[Company]:
        """Get a company by its ID and return it.

        If a company with that ID does not exist, return a 404 response
        """
        result: "ScalarResult" = await async_session.scalars(select(Company).where(Company.id == company_id))
        company: Optional[Company] = result.one_or_none()
        if not company:
            raise HTTPException(detail=f"Company with ID {company_id} not found", status_code=HTTP_404_NOT_FOUND)
        return CreateCompanyDTO.from_orm(company)

    @get()
    async def get_all_companies(self, async_session: AsyncSession) -> List[DTO[Company]]:
        """Get all companies from the database."""
        companies: "ScalarResult" = await async_session.scalars(select(Company))
        return [CreateCompanyDTO.from_orm(company) for company in companies.all()]


sqlalchemy_config = SQLAlchemyConfig(
    # "async_session" will be the name of the dependency of SQLAlchemy AsyncSession instance.
    connection_string="sqlite+aiosqlite:///test.sqlite",
    dependency_key="async_session",
)
sqlalchemy_plugin = SQLAlchemyPlugin(config=sqlalchemy_config)

dto_factory = DTOFactory(plugins=[sqlalchemy_plugin])
CreateCompanyDTO = dto_factory("CreateCompanyDTO", Company, exclude=["id"])


async def on_startup() -> None:
    """Initialize the database."""
    async with sqlalchemy_config.engine.begin() as conn:  # type: ignore
        await conn.run_sync(Base.metadata.create_all)  # pyright: ignore


app = Starlite(
    route_handlers=[CompanyController],
    on_startup=[on_startup],
    plugins=[sqlalchemy_plugin],
)
