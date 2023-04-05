from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from typing_extensions import Annotated

from starlite import Starlite, get, post
from starlite.dto.factory import DTOConfig, dto_field
from starlite.dto.factory.stdlib import DataclassDTO


@dataclass
class Company:
    name: str
    worth: float
    id: int = field(metadata=dto_field("read-only"), default=-1)
    super_secret: str = field(metadata=dto_field("private"), default_factory=lambda: "generated")


CompanyWriteDTO = DataclassDTO[Annotated[Company, DTOConfig(purpose="write")]]
CompanyReadDTO = DataclassDTO[Annotated[Company, DTOConfig(purpose="read")]]
CompanyListDTO = DataclassDTO[Annotated[List[Company], DTOConfig(purpose="read")]]


@post(data_dto=CompanyWriteDTO, return_dto=CompanyReadDTO)
def create_company(data: Company) -> Company:
    data.id = 1234567
    return data


@get(return_dto=CompanyListDTO)
def list_companies() -> List[Company]:
    return [Company(id=1, name="mega-corp", worth=123.45, super_secret="shh")]


app = Starlite(route_handlers=[create_company, list_companies], preferred_validation_backend="pydantic")
