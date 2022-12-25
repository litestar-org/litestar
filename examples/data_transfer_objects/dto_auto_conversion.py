from typing import List
from starlite import get, HTTPException
from sqlalchemy import Column, Float, Integer, String
from sqlalchemy.orm import declarative_base
from starlite import DTOFactory
from starlite.plugins.sql_alchemy import SQLAlchemyPlugin
from starlite.status_codes import HTTP_404_NOT_FOUND

dto_factory = DTOFactory(plugins=[SQLAlchemyPlugin()])

Base = declarative_base()


class Company(Base):
    id = Column(Integer, primary_key=True)
    name = Column(String)
    worth = Column(Float)
    secret = Column(String)


ReadCompanyDTO = dto_factory("CompanyDTO", Company, exclude=["secret"])

companies: List[Company] = [
    Company(id=1, name="My Firm", worth=1000000.0, secret="secret"),
    Company(id=2, name="My New Firm", worth=1000.0, secret="abc123"),
]


@get("/{company_id: int}")
def get_company(company_id: int) -> ReadCompanyDTO:
    try:
        return companies[company_id - 1]
    except IndexError:
        raise HTTPException(
            detail="Company not found",
            status_code=HTTP_404_NOT_FOUND,
        )


@get()
def get_companies() -> List[ReadCompanyDTO]:
    return companies