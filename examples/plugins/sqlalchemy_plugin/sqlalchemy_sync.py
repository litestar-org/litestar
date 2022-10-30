from typing import Optional

from sqlalchemy import Column, Float, Integer, String, select
from sqlalchemy.orm import Session, declarative_base

from starlite import DTOFactory, Starlite, get, post
from starlite.plugins.sql_alchemy import SQLAlchemyConfig, SQLAlchemyPlugin

Base = declarative_base()

sqlalchemy_config = SQLAlchemyConfig(connection_string="sqlite+pysqlite://", use_async_engine=False)
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
    Base.metadata.create_all(sqlalchemy_config.engine)  # type: ignore


@post(path="/companies")
def create_company(
    data: CreateCompanyDTO,  # type: ignore
    db_session: Session,
) -> Company:
    company = Company(**data.dict())
    db_session.add(company)
    db_session.commit()
    return company


@get(path="/companies/{company_id:int}")
def get_company(company_id: str, db_session: Session) -> Optional[Company]:
    return db_session.scalar(select(Company).where(Company.id == company_id))


app = Starlite(
    route_handlers=[create_company, get_company],
    on_startup=[on_startup],
    plugins=[sqlalchemy_plugin],
)
