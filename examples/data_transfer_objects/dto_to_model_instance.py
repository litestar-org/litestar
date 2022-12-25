from sqlalchemy import Column, Float, Integer, String
from sqlalchemy.orm import Mapped, declarative_base

from starlite import DTOFactory, post
from starlite.plugins.sql_alchemy import SQLAlchemyPlugin

dto_factory = DTOFactory(plugins=[SQLAlchemyPlugin()])

Base = declarative_base()


class Company(Base):  # pyright: ignore
    __tablename__ = "company"

    id: Mapped[int] = Column(Integer, primary_key=True)  # type: ignore
    name: Mapped[str] = Column(String)  # type: ignore
    worth: Mapped[float] = Column(Float)  # type: ignore


CompanyDTO = dto_factory("CompanyDTO", Company)


@post()
def create_company(data: CompanyDTO) -> Company:  # type: ignore
    return data.to_model_instance()
