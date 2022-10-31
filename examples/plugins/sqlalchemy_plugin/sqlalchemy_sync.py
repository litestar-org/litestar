from typing import Optional

from sqlalchemy import Column, Float, Integer, String, select
from sqlalchemy.orm import Session, declarative_base

from starlite import DTOFactory, Starlite, get, post
from starlite.plugins.sql_alchemy import SQLAlchemyConfig, SQLAlchemyPlugin

Base = declarative_base()

sqlalchemy_config = SQLAlchemyConfig(connection_string="sqlite+pysqlite://", use_async_engine=False)
sqlalchemy_plugin = SQLAlchemyPlugin(config=sqlalchemy_config)
dto_factory = DTOFactory(plugins=[sqlalchemy_plugin])


class Company(Base):  # pyright: ignore
    __tablename__ = "company"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    worth = Column(Float)


CreateCompanyDTO = dto_factory("CreateCompanyDTO", Company, exclude=["id"])


async def on_startup() -> None:
    """Initialize the database."""
    Base.metadata.create_all(sqlalchemy_config.engine)  # type: ignore


@post(path="/companies")
def create_company(
    data: CreateCompanyDTO,  # type: ignore[valid-type]
    db_session: Session,
) -> Company:
    """Create a new company and return it."""
    company: Company = data.to_model_instance()  # type: ignore[attr-defined]
    db_session.add(company)
    db_session.commit()
    return company


@get(path="/companies/{company_id:int}")
def get_company(company_id: str, db_session: Session) -> Optional[Company]:
    """Get a company by ID and return it if found, else return None."""
    return db_session.scalars(select(Company).where(Company.id == company_id)).one_or_none()


app = Starlite(
    route_handlers=[create_company, get_company],
    on_startup=[on_startup],
    plugins=[sqlalchemy_plugin],
)
