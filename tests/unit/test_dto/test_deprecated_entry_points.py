from __future__ import annotations

import dataclasses
import gc
import warnings
from typing import Annotated, Any

import msgspec
import pytest

from litestar import Litestar, Request, post, websocket_listener
from litestar._openapi.schema_generation import SchemaCreator
from litestar._openapi.schema_generation.plugins import openapi_schema_plugins
from litestar.dto import AbstractDTO, DataclassDTO, DTOConfig, MsgspecDTO
from litestar.exceptions import DTOFactoryException, InvalidAnnotationException, LitestarDeprecationWarning
from litestar.handlers import HTTPRouteHandler
from litestar.openapi.spec import Reference
from litestar.params import JSONBody, URLEncodedBody
from litestar.testing import RequestFactory, TestClient
from litestar.typing import FieldDefinition
from tests.unit.test_dto import Model, registered

PAYLOAD = b'{"a":1,"b":"two"}'


def make_handler(dto: Any = DataclassDTO[Model], return_dto: Any = DataclassDTO[Model]) -> HTTPRouteHandler:
    @post("/", dto=dto, return_dto=return_dto)
    async def handler(data: JSONBody[Model]) -> Model:
        return data

    return handler


@pytest.fixture
def handler_and_request() -> tuple[HTTPRouteHandler, Request[Any, Any, Any]]:
    app = Litestar([make_handler()])
    handler = registered(app)
    return handler, RequestFactory(app=app).post("/", route_handler=handler)


@pytest.mark.parametrize("name", ["decode_bytes", "decode_builtins", "data_to_encodable_type"])
def test_instance_method_called_directly_warns(
    name: str, handler_and_request: tuple[HTTPRouteHandler, Request[Any, Any, Any]]
) -> None:
    handler, request = handler_and_request
    assert handler.data_dto is not None
    assert handler._dto_plan is not None and handler._dto_plan.encode is not None
    with pytest.warns(LitestarDeprecationWarning, match="AbstractDTO.__init__") as init_record:
        dto = handler.data_dto(request)
    assert init_record[0].filename == __file__
    arguments: dict[str, Any] = {
        "decode_bytes": PAYLOAD,
        "decode_builtins": {"a": 1, "b": "two"},
        "data_to_encodable_type": Model(a=1, b="two"),
    }
    expected = (
        handler._dto_plan.encode(Model(a=1, b="two")) if name == "data_to_encodable_type" else Model(a=1, b="two")
    )

    with pytest.warns(LitestarDeprecationWarning, match=f"AbstractDTO.{name}") as record:
        result = getattr(dto, name)(arguments[name])

    assert result == expected
    assert record[0].filename == __file__
    assert "There is no replacement for decoding or encoding with a DTO outside a route handler yet" in str(
        record[0].message
    )


def test_create_for_field_definition_warns_and_validates() -> None:
    dto = DataclassDTO[Model]

    with pytest.warns(LitestarDeprecationWarning, match="AbstractDTO.create_for_field_definition") as record:
        result = dto.create_for_field_definition(FieldDefinition.from_annotation(JSONBody[Model]), handler_id="h")
    assert result is None
    assert record[0].filename == __file__

    with pytest.warns(LitestarDeprecationWarning), pytest.raises(InvalidAnnotationException):
        dto.create_for_field_definition(FieldDefinition.from_annotation(tuple[Model, str]), handler_id="h")


def test_direct_backend_serves_the_direction_the_plan_lacks_on_its_class_only() -> None:
    class DirectDTO(DataclassDTO[Model]):
        pass

    class ChildDTO(DirectDTO):
        pass

    app = Litestar([make_handler(DataclassDTO[Model], None)])
    handler: HTTPRouteHandler = registered(app)
    request = RequestFactory(app=app).post("/", route_handler=handler)

    with pytest.warns(LitestarDeprecationWarning):
        DirectDTO.create_for_field_definition(FieldDefinition.from_annotation(Model), handler_id=handler.handler_id)
        encoded = DirectDTO(request).data_to_encodable_type(Model(a=1, b="two"))
        with pytest.raises(DTOFactoryException) as exc_info:
            ChildDTO(request).data_to_encodable_type(Model(a=1, b="two"))

    assert msgspec.to_builtins(encoded) == {"a": 1, "b": "two"}
    assert str(exc_info.value) == (
        f"Handler {str(handler)!r} has no return DTO, and no backend of {ChildDTO.__qualname__} was created for it"
    )
    assert list(vars(DirectDTO)["_direct_backends"]) == [handler.handler_id]
    assert "_direct_backends" not in vars(DataclassDTO)


def openapi_component(dto: type[AbstractDTO[Any]], field_definition: Any, handler_id: str) -> tuple[str, Any]:
    schema_creator = SchemaCreator(plugins=openapi_schema_plugins)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        result = dto.create_openapi_schema(field_definition, handler_id, schema_creator)
    components = schema_creator.schema_registry.generate_components_schemas()
    assert isinstance(result, Reference)
    name = result.ref.rsplit("/", 1)[1]
    return name, components[name]


def test_create_openapi_schema_documents_each_direction_without_warning() -> None:
    data_dto = DataclassDTO[Annotated[Model, DTOConfig(exclude={"a"})]]
    return_dto = DataclassDTO[Annotated[Model, DTOConfig(exclude={"b"})]]
    handler: HTTPRouteHandler = registered(Litestar([make_handler(data_dto, return_dto)]))
    handler_id = f"{handler.handler_id}"

    request_name, request_schema = openapi_component(data_dto, handler.parsed_data_field, handler_id)
    response_name, response_schema = openapi_component(return_dto, handler.parsed_return_field, handler_id)

    assert (request_name, set(request_schema.properties)) == ("HandlerModelRequestBody", {"b"})
    assert (response_name, set(response_schema.properties)) == ("HandlerModelResponseBody", {"a"})


def test_create_openapi_schema_treats_only_the_listener_data_field_itself_as_received_data() -> None:
    @websocket_listener("/ws", dto=DataclassDTO[Model])
    async def listener(data: Model) -> Model:
        return data

    handler = registered(Litestar([listener]), "/ws", "websocket")

    copied_field = dataclasses.replace(handler.parsed_data_field)

    assert openapi_component(DataclassDTO[Model], handler.parsed_data_field, handler.handler_id)[0].endswith(
        "RequestBody"
    )
    assert openapi_component(DataclassDTO[Model], copied_field, handler.handler_id)[0].endswith("ResponseBody")


def test_create_openapi_schema_does_not_find_a_collected_handler() -> None:
    app = Litestar([make_handler()])
    field_definition = registered(app).parsed_data_field
    handler_id = registered(app).handler_id

    del app
    gc.collect()
    with pytest.raises(DTOFactoryException):
        DataclassDTO[Model].create_openapi_schema(field_definition, handler_id, SchemaCreator())


class StructModel(msgspec.Struct):
    a: int
    b: str


def in_tree_dto(kind: str) -> tuple[type[AbstractDTO[Any]], type[Any]]:
    if kind == "dataclass":
        return DataclassDTO[Model], Model
    if kind == "msgspec":
        return MsgspecDTO[StructModel], StructModel
    if kind == "sqlalchemy":
        alchemy = pytest.importorskip("advanced_alchemy.extensions.litestar")
        orm = pytest.importorskip("sqlalchemy.orm")
        base = type("Base", (orm.DeclarativeBase,), {})
        row = type(
            "Row",
            (base,),
            {
                "__tablename__": "row",
                "__annotations__": {"a": orm.Mapped[int], "b": orm.Mapped[str]},
                "a": orm.mapped_column(primary_key=True),
            },
        )
        return alchemy.SQLAlchemyDTO[row], row
    pydantic = pytest.importorskip("pydantic")
    from litestar.plugins.pydantic import PydanticDTO

    pydantic_model = pydantic.create_model("PydanticModel", a=(int, ...), b=(str, ...))
    return PydanticDTO[pydantic_model], pydantic_model


@pytest.mark.parametrize("kind", ["dataclass", "msgspec", "pydantic", "sqlalchemy"])
def test_in_tree_dtos_emit_no_deprecation_warning(kind: str) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", LitestarDeprecationWarning)
        dto, model = in_tree_dto(kind)

        @post("/json", dto=dto, signature_namespace={"M": model})
        async def json_handler(data: JSONBody[M]) -> M:  # type: ignore[valid-type]  # noqa: F821
            return data

        @post("/form", dto=dto, signature_namespace={"M": model})
        async def form_handler(data: URLEncodedBody[M]) -> M:  # type: ignore[valid-type]  # noqa: F821
            return data

        app = Litestar([json_handler, form_handler])
        with TestClient(app) as client:
            assert client.post("/json", content=PAYLOAD).json() == {"a": 1, "b": "two"}
            assert client.post("/form", data={"a": "1", "b": "two"}).json() == {"a": 1, "b": "two"}
        assert app.openapi_schema.components.schemas


def test_overriding_a_deprecated_entry_point_warns_once_per_class_and_method() -> None:
    class OverridingDTO(DataclassDTO[Model]):
        def decode_bytes(self, value: bytes) -> Any:
            return None

        @classmethod
        def create_openapi_schema(
            cls, field_definition: FieldDefinition, handler_id: str, schema_creator: SchemaCreator
        ) -> Any:
            return None

    with pytest.warns(LitestarDeprecationWarning) as record:
        Litestar([make_handler(OverridingDTO, OverridingDTO)])
        Litestar([make_handler(OverridingDTO, None)])

    assert [str(warning.message) for warning in record] == [
        f"test_overriding_a_deprecated_entry_point_warns_once_per_class_and_method.<locals>.OverridingDTO overrides "
        f"AbstractDTO.{name}, which is deprecated since litestar 3.0 and no longer called: the override has no "
        "effect. The method will be removed in 4.0."
        for name in ("decode_bytes", "create_openapi_schema")
    ]
