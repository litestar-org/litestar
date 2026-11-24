from typing import Optional

import pytest
from advanced_alchemy.extensions.litestar import SQLAlchemyDTO, SQLAlchemyDTOConfig
from advanced_alchemy.extensions.litestar.plugins import (
    SQLAlchemyInitPlugin,
    SQLAlchemySerializationPlugin,
    SQLAlchemySyncConfig,
)
from advanced_alchemy.filters import LimitOffset
from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from litestar import get, post
from litestar.di import NamedDependency
from litestar.params import JSONBody
from litestar.testing import create_test_client


# advanced-alchemy's 'db_session' provider declares 'scope: Scope'
@pytest.mark.filterwarnings(
    "ignore:.*Parameter 'scope' declares 'Scope':litestar.exceptions.LitestarDeprecationWarning"
)
def test_using_pagination() -> None:
    # https://github.com/litestar-org/litestar/issues/2358
    async def provide_limit_offset_pagination() -> LimitOffset:
        return LimitOffset(limit=0, offset=0)

    @get(
        path="/",
        dependencies={"limit_offset": provide_limit_offset_pagination},
    )
    async def handler(limit_offset: NamedDependency[LimitOffset]) -> None:
        return None

    with create_test_client(
        route_handlers=[handler],
        plugins=[SQLAlchemyInitPlugin(SQLAlchemySyncConfig(connection_string="sqlite:///"))],
    ) as client:
        assert client.get("/").status_code == 200


class SmokeBase(DeclarativeBase): ...


class SmokeUser(SmokeBase):
    __tablename__ = "dto_smoke_user"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    password: Mapped[str]


class SmokeReadDTO(SQLAlchemyDTO[SmokeUser]):
    config = SQLAlchemyDTOConfig(exclude={"password"})


SMOKE_PAYLOAD = {"id": 1, "name": "a", "password": "x"}


def test_sqlalchemy_dto_explicit_and_plugin_round_trip() -> None:
    @post("/explicit", dto=SQLAlchemyDTO[SmokeUser], return_dto=SmokeReadDTO, sync_to_thread=False)
    def explicit(data: JSONBody[SmokeUser]) -> SmokeUser:
        return data

    @post("/implicit", sync_to_thread=False)
    def implicit(data: JSONBody[SmokeUser]) -> list[SmokeUser]:
        return [data]

    with create_test_client(route_handlers=[explicit, implicit], plugins=[SQLAlchemySerializationPlugin()]) as client:
        explicit_response = client.post("/explicit", json=SMOKE_PAYLOAD)
        implicit_response = client.post("/implicit", json=SMOKE_PAYLOAD)
        schemas = client.get("/schema/openapi.json").json()["components"]["schemas"]
        registered = client.app.route_handler_method_map["/implicit"]["POST"]

    assert (explicit_response.status_code, explicit_response.json()) == (201, {"id": 1, "name": "a"})
    assert (implicit_response.status_code, implicit_response.json()) == (201, [SMOKE_PAYLOAD])
    assert registered.data_dto is registered.return_dto
    assert registered.data_dto is not None
    assert issubclass(registered.data_dto, SQLAlchemyDTO)
    dto_components = [name for name in schemas if name.endswith(("RequestBody", "ResponseBody"))]
    assert len(dto_components) == 4
    assert sum(name.endswith("SmokeUserRequestBody") for name in dto_components) == 2
    assert sum(name.endswith("SmokeUserResponseBody") for name in dto_components) == 2


class SmokeAddress(SmokeBase):
    __tablename__ = "dto_smoke_address"
    id: Mapped[int] = mapped_column(primary_key=True)
    street: Mapped[str]
    city: Mapped[str]


class SmokePerson(SmokeBase):
    __tablename__ = "dto_smoke_person"
    id: Mapped[int] = mapped_column(primary_key=True)
    address_id: Mapped[Optional[int]] = mapped_column(ForeignKey("dto_smoke_address.id"))
    address: Mapped[Optional[SmokeAddress]] = relationship()


def test_sqlalchemy_dto_exclude_reaches_through_optional_relationship() -> None:
    class PersonDTO(SQLAlchemyDTO[SmokePerson]):
        config = SQLAlchemyDTOConfig(exclude={"address_id", "address.street"})

    @get("/", return_dto=PersonDTO, sync_to_thread=False)
    def read_person() -> SmokePerson:
        return SmokePerson(id=1, address=SmokeAddress(id=2, street="s", city="c"))

    with create_test_client(route_handlers=[read_person]) as client:
        response = client.get("/").json()
        schemas = client.get("/schema/openapi.json").json()["components"]["schemas"]

    assert response == {"id": 1, "address": {"id": 2, "city": "c"}}
    assert [sorted(schema["properties"]) for name, schema in schemas.items() if "SmokeAddress" in name] == [
        ["city", "id"]
    ]
