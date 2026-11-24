import pytest
from advanced_alchemy.extensions.litestar import SQLAlchemyDTO, SQLAlchemyDTOConfig
from advanced_alchemy.extensions.litestar.plugins import (
    SQLAlchemyInitPlugin,
    SQLAlchemySerializationPlugin,
    SQLAlchemySyncConfig,
)
from advanced_alchemy.filters import LimitOffset
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

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


def test_sqlalchemy_dto_explicit_round_trip() -> None:
    @post("/", dto=SQLAlchemyDTO[SmokeUser], return_dto=SmokeReadDTO, sync_to_thread=False)
    def handler(data: JSONBody[SmokeUser]) -> SmokeUser:
        return data

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post("/", json=SMOKE_PAYLOAD)
        assert response.status_code == 201
        assert response.json() == {"id": 1, "name": "a"}


def test_sqlalchemy_serialization_plugin_round_trip() -> None:
    @post("/", sync_to_thread=False)
    def handler(data: JSONBody[SmokeUser]) -> list[SmokeUser]:
        return [data]

    with create_test_client(route_handlers=[handler], plugins=[SQLAlchemySerializationPlugin()]) as client:
        response = client.post("/", json=SMOKE_PAYLOAD)
        assert response.status_code == 201
        assert response.json() == [SMOKE_PAYLOAD]

        registered = client.app.route_handler_method_map["/"]["POST"]
        assert registered.data_dto is registered.return_dto
        assert registered.data_dto is not None
        assert issubclass(registered.data_dto, SQLAlchemyDTO)


def test_sqlalchemy_dto_openapi_component_names() -> None:
    @post("/explicit", dto=SQLAlchemyDTO[SmokeUser], return_dto=SmokeReadDTO, sync_to_thread=False)
    def explicit(data: JSONBody[SmokeUser]) -> SmokeUser:
        return data

    @post("/implicit", sync_to_thread=False)
    def implicit(data: JSONBody[SmokeUser]) -> list[SmokeUser]:
        return [data]

    with create_test_client(route_handlers=[explicit, implicit], plugins=[SQLAlchemySerializationPlugin()]) as client:
        schemas = client.get("/schema/openapi.json").json()["components"]["schemas"]

    dto_components = [name for name in schemas if name.endswith(("RequestBody", "ResponseBody"))]
    assert len(dto_components) == 4
    assert sum(name.endswith("SmokeUserRequestBody") for name in dto_components) == 2
    assert sum(name.endswith("SmokeUserResponseBody") for name in dto_components) == 2
