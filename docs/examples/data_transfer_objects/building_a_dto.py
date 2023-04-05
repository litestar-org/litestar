from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

import msgspec

from starlite import Starlite, put
from starlite.contrib.sqlalchemy.base import Base
from starlite.dto.interface import AbstractDTOInterface

if TYPE_CHECKING:
    from starlite.connection import Request
    from starlite.types.serialization import StarliteEncodableType


class Company(Base):
    name: str
    worth: float


class CompanySchema(msgspec.Struct):
    id: UUID
    name: str
    worth: float


class CompanyDTO(AbstractDTOInterface[Company]):
    def __init__(self, data: Company) -> None:
        self._data = data

    def to_data_type(self) -> Company:
        return self._data

    def to_encodable_type(self, **kwargs: Any) -> bytes | StarliteEncodableType:
        return CompanySchema(id=self._data.id, name=self._data.name, worth=self._data.worth)

    @classmethod
    async def from_connection(cls, request: Request) -> CompanyDTO:
        parsed_data = msgspec.json.decode(await request.body(), type=CompanySchema)
        return cls(data=Company(id=parsed_data.id, name=parsed_data.name, worth=parsed_data.worth))

    @classmethod
    def from_data(cls, data: Company) -> CompanyDTO:
        return cls(data=data)


@put("/companies/{company_id:uuid}", data_dto=CompanyDTO, return_dto=CompanyDTO)
async def update_company(company_id: UUID, data: Company) -> Company:
    return data


app = Starlite(route_handlers=[update_company])
