from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import msgspec

from litestar import Litestar, put
from litestar.contrib.sqlalchemy.base import Base
from litestar.dto.interface import DTOInterface

if TYPE_CHECKING:
    from litestar.connection import Request
    from litestar.types.serialization import LitestarEncodableType


class Company(Base):
    name: str
    worth: float


class CompanySchema(msgspec.Struct):
    id: UUID
    name: str
    worth: float


class CompanyDTO(DTOInterface[Company]):
    def __init__(self, data: Company) -> None:
        self._data = data

    def to_data_type(self) -> Company:
        return self._data

    def to_encodable_type(self) -> bytes | LitestarEncodableType:
        return CompanySchema(id=self._data.id, name=self._data.name, worth=self._data.worth)

    @classmethod
    def from_bytes(cls, raw: bytes, connection: Request) -> CompanyDTO:
        parsed_data = msgspec.json.decode(raw, type=CompanySchema)
        return cls(data=Company(id=parsed_data.id, name=parsed_data.name, worth=parsed_data.worth))

    @classmethod
    def from_data(cls, data: Company, connection: Request) -> CompanyDTO:
        return cls(data=data)


@put("/companies/{company_id:uuid}", data_dto=CompanyDTO, return_dto=CompanyDTO)
async def update_company(company_id: UUID, data: Company) -> Company:
    return data


app = Litestar(route_handlers=[update_company])
