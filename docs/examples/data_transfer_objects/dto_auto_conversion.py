from typing import List

from sqlalchemy import Column, Float, Integer, String
from sqlalchemy.orm import Mapped, declarative_base

from litestar import Litestar, get
from litestar.contrib.sqlalchemy_1.plugin import SQLAlchemyPlugin
from litestar.dto import DTOFactory
from litestar.exceptions import HTTPException
from litestar.status_codes import HTTP_404_NOT_FOUND

sqlalchemy_plugin = SQLAlchemyPlugin()
dto_factory = DTOFactory(plugins=[sqlalchemy_plugin])

Base = declarative_base()


class Company(Base):  # pyright: ignore
    __tablename__ = "company"

    id: Mapped[int] = Column(Integer, primary_key=True)  # pyright: ignore
    name: Mapped[str] = Column(String)  # pyright: ignore
    worth: Mapped[float] = Column(Float)  # pyright: ignore
    secret: Mapped[str] = Column(String)  # pyright: ignore


ReadCompanyDTO = dto_factory("CompanyDTO", Company, exclude=["secret"])

companies: List[Company] = [
    Company(id=1, name="My Firm", worth=1000000.0, secret="secret"),
    Company(id=2, name="My New Firm", worth=1000.0, secret="abc123"),
]


@get("/{company_id: int}")
def get_company(company_id: int) -> ReadCompanyDTO:  # type: ignore
    try:
        return companies[company_id - 1]
    except IndexError:
        raise HTTPException(
            detail="Company not found",
            status_code=HTTP_404_NOT_FOUND,
        )


@get()
def get_companies() -> List[ReadCompanyDTO]:  # type: ignore
    return companies


app = Litestar(
    route_handlers=[get_company, get_companies],
    plugins=[sqlalchemy_plugin],
)
