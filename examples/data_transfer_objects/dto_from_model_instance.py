from sqlalchemy import Column, Float, Integer, String
from sqlalchemy.orm import Mapped, declarative_base

from starlite import DTOFactory
from starlite.plugins.sql_alchemy import SQLAlchemyPlugin

dto_factory = DTOFactory(plugins=[SQLAlchemyPlugin()])

Base = declarative_base()


class Company(Base):  # pyright: ignore
    id: Mapped[int] = Column(Integer, primary_key=True)  # type: ignore
    name: Mapped[str] = Column(String)  # type: ignore
    worth: Mapped[float] = Column(Float)  # type: ignore


CompanyDTO = dto_factory("CompanyDTO", Company)

company_instance = Company(id=1, name="My Firm", worth=1000000.0)

dto_instance = CompanyDTO.from_model_instance(company_instance)
