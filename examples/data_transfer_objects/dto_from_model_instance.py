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

company_instance = Company(id=1, name="My Firm", worth=1000000.0)

dto_instance = CompanyDTO.from_model_instance(company_instance)