from sqlalchemy import Column, Float, Integer, String
from sqlalchemy.orm import Mapped, declarative_base

from starlite.contrib.sqlalchemy_1.plugin import SQLAlchemyPlugin
from starlite.dto import DTOFactory

dto_factory = DTOFactory(plugins=[SQLAlchemyPlugin()])

Base = declarative_base()


class Company(Base):  # pyright: ignore
    __tablename__ = "company"

    id: Mapped[int] = Column(Integer, primary_key=True)  # pyright: ignore
    name: Mapped[str] = Column(String)  # pyright: ignore
    worth: Mapped[float] = Column(Float)  # pyright: ignore


CompanyDTO = dto_factory("CompanyDTO", Company)

company_instance = Company(id=1, name="My Firm", worth=1000000.0)

dto_instance = CompanyDTO.from_model_instance(company_instance)
