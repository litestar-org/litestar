from starlite import post
from sqlalchemy import Column, Float, Integer, String
from sqlalchemy.orm import declarative_base
from starlite import DTOFactory
from starlite.plugins.sql_alchemy import SQLAlchemyPlugin

dto_factory = DTOFactory(plugins=[SQLAlchemyPlugin()])

Base = declarative_base()


class Company(Base):
    id = Column(Integer, primary_key=True)
    name = Column(String)
    worth = Column(Float)


CompanyDTO = dto_factory("CompanyDTO", Company)


@post()
def create_company(data: CompanyDTO) -> Company:
    return data.to_model_instance()