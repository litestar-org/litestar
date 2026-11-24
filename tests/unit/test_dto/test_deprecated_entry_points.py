from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Any, ClassVar

import msgspec
import pytest

from litestar import Litestar, Request, post
from litestar._openapi.schema_generation import SchemaCreator
from litestar._openapi.schema_generation.plugins import openapi_schema_plugins
from litestar.dto import AbstractDTO, DataclassDTO, MsgspecDTO
from litestar.dto._backend import DTOBackend
from litestar.exceptions import DTOFactoryException, InvalidAnnotationException, LitestarDeprecationWarning
from litestar.handlers import HTTPRouteHandler
from litestar.openapi.spec import Reference, Schema
from litestar.params import JSONBody, URLEncodedBody
from litestar.testing import RequestFactory, TestClient
from litestar.typing import FieldDefinition


@dataclass
class Model:
    a: int
    b: str


PAYLOAD = b'{"a":1,"b":"two"}'


def make_handler(dto: Any = DataclassDTO[Model], return_dto: Any = DataclassDTO[Model]) -> HTTPRouteHandler:
    @post("/", dto=dto, return_dto=return_dto)
    async def handler(data: JSONBody[Model]) -> Model:
        return data

    return handler


@pytest.fixture
def registered() -> tuple[HTTPRouteHandler, Request[Any, Any, Any]]:
    app = Litestar([make_handler()])
    handler = app.route_handler_method_map["/"]["POST"]
    return handler, RequestFactory(app=app).post("/", route_handler=handler)  # type: ignore[return-value]


@pytest.mark.parametrize("name", ["decode_bytes", "decode_builtins", "data_to_encodable_type"])
def test_instance_method_called_directly_warns(
    name: str, registered: tuple[HTTPRouteHandler, Request[Any, Any, Any]]
) -> None:
    handler, request = registered
    assert handler.data_dto is not None
    assert handler._dto_plan is not None and handler._dto_plan.encode is not None
    dto = handler.data_dto(request)
    arguments: dict[str, Any] = {
        "decode_bytes": PAYLOAD,
        "decode_builtins": {"a": 1, "b": "two"},
        "data_to_encodable_type": Model(a=1, b="two"),
    }
    expected = (
        handler._dto_plan.encode(Model(a=1, b="two"), request)
        if name == "data_to_encodable_type"
        else Model(a=1, b="two")
    )

    with pytest.warns(LitestarDeprecationWarning, match=f"AbstractDTO.{name}") as record:
        result = getattr(dto, name)(arguments[name])

    assert result == expected
    assert record[0].filename == __file__


def test_instance_method_on_unregistered_handler_raises() -> None:
    handler = make_handler()
    request = RequestFactory().post("/", route_handler=handler)

    with pytest.warns(LitestarDeprecationWarning), pytest.raises(DTOFactoryException):
        DataclassDTO[Model](request).decode_bytes(PAYLOAD)


def test_create_for_field_definition_warns_and_validates() -> None:
    dto = DataclassDTO[Model]

    with pytest.warns(LitestarDeprecationWarning, match="AbstractDTO.create_for_field_definition") as record:
        result = dto.create_for_field_definition(FieldDefinition.from_annotation(JSONBody[Model]), handler_id="h")
    assert result is None
    assert record[0].filename == __file__

    with pytest.warns(LitestarDeprecationWarning), pytest.raises(InvalidAnnotationException):
        dto.create_for_field_definition(FieldDefinition.from_annotation(tuple[Model, str]), handler_id="h")


def test_direct_create_for_field_definition_keeps_shims_working() -> None:
    class DirectDTO(DataclassDTO[Model]):
        pass

    handler = make_handler()
    request = RequestFactory().post("/", route_handler=handler)
    field_definition = FieldDefinition.from_annotation(JSONBody[Model])

    with pytest.warns(LitestarDeprecationWarning):
        DirectDTO.create_for_field_definition(field_definition, handler_id=handler.handler_id)
        assert DirectDTO(request).decode_bytes(PAYLOAD) == Model(a=1, b="two")
        assert DirectDTO(request).decode_builtins({"a": 1, "b": "two"}) == Model(a=1, b="two")
        schema = DirectDTO.create_openapi_schema(
            field_definition, handler.handler_id, SchemaCreator(plugins=openapi_schema_plugins)
        )
        assert isinstance(schema, Reference)
        assert schema.ref.endswith("ModelRequestBody")

        DirectDTO.create_for_field_definition(
            FieldDefinition.from_annotation(JSONBody[list[Model]]), handler_id=handler.handler_id
        )
        assert DirectDTO(request).decode_bytes(b"[" + PAYLOAD + b"]") == [Model(a=1, b="two")]

        class ChildDTO(DirectDTO):
            pass

        with pytest.raises(DTOFactoryException):
            ChildDTO(request).decode_bytes(PAYLOAD)

    assert "_direct_backends" not in vars(AbstractDTO)
    assert "_direct_backends" not in vars(DataclassDTO)
    assert list(vars(DirectDTO)["_direct_backends"]) == [str(handler.handler_id)]


def test_create_openapi_schema_does_not_warn(registered: tuple[HTTPRouteHandler, Request[Any, Any, Any]]) -> None:
    handler, _ = registered
    assert handler.data_dto is not None
    assert handler.parsed_data_field is not None

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        schema = handler.data_dto.create_openapi_schema(
            field_definition=handler.parsed_data_field,
            handler_id=handler.handler_id,
            schema_creator=SchemaCreator(plugins=openapi_schema_plugins),
        )

    assert isinstance(schema, Reference)


class OverridingDTO(DataclassDTO[Model]):
    calls: ClassVar[list[str]] = []

    def decode_bytes(self, value: bytes) -> Any:
        self.calls.append("decode_bytes")
        return super().decode_bytes(value)

    def decode_builtins(self, value: dict[str, Any]) -> Any:
        self.calls.append("decode_builtins")
        return super().decode_builtins(value)

    def data_to_encodable_type(self, data: Any) -> Any:
        self.calls.append("data_to_encodable_type")
        return super().data_to_encodable_type(data)

    @classmethod
    def create_for_field_definition(
        cls, field_definition: FieldDefinition, handler_id: str, backend_cls: type[DTOBackend] | None = None
    ) -> None:
        cls.calls.append("create_for_field_definition")
        super().create_for_field_definition(field_definition=field_definition, handler_id=handler_id)

    @classmethod
    def create_openapi_schema(
        cls, field_definition: FieldDefinition, handler_id: str, schema_creator: SchemaCreator
    ) -> Reference | Schema:
        cls.calls.append("create_openapi_schema")
        return super().create_openapi_schema(field_definition, handler_id, schema_creator)


def test_overriding_class_emits_no_warning_and_is_called() -> None:
    @post("/json", dto=OverridingDTO)
    async def json_handler(data: JSONBody[Model]) -> Model:
        return data

    @post("/form", dto=OverridingDTO, return_dto=None)
    async def form_handler(data: URLEncodedBody[Model]) -> None:
        return None

    OverridingDTO.calls.clear()
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        app = Litestar([json_handler, form_handler])
        assert OverridingDTO.calls == ["create_for_field_definition"] * 3
        with TestClient(app) as client:
            assert client.post("/json", content=PAYLOAD).json() == {"a": 1, "b": "two"}
            assert client.post("/form", data={"a": "1", "b": "two"}).status_code == 201
        assert app.openapi_schema.components.schemas

    assert OverridingDTO.calls[3:] == [
        "decode_bytes",
        "data_to_encodable_type",
        "decode_builtins",
        "create_openapi_schema",
        "create_openapi_schema",
        "create_openapi_schema",
    ]


def test_instance_method_on_registered_handler_without_dto_for_direction_raises() -> None:
    app = Litestar([make_handler(DataclassDTO[Model], None)])
    handler: HTTPRouteHandler = app.route_handler_method_map["/"]["POST"]  # type: ignore[assignment]
    request = RequestFactory(app=app).post("/", route_handler=handler)

    with pytest.warns(LitestarDeprecationWarning), pytest.raises(DTOFactoryException, match="no return DTO"):
        OtherDTO(request).data_to_encodable_type(Model(a=1, b="two"))


class StructModel(msgspec.Struct):
    a: int
    b: str


def in_tree_dto(kind: str) -> tuple[type[AbstractDTO[Any]], type[Any]]:
    if kind == "dataclass":
        return DataclassDTO[Model], Model
    if kind == "msgspec":
        return MsgspecDTO[StructModel], StructModel
    pydantic = pytest.importorskip("pydantic")
    from litestar.plugins.pydantic import PydanticDTO

    pydantic_model = pydantic.create_model("PydanticModel", a=(int, ...), b=(str, ...))
    return PydanticDTO[pydantic_model], pydantic_model


@pytest.mark.parametrize("kind", ["dataclass", "msgspec", "pydantic"])
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


class OtherDTO(DataclassDTO[Model]):
    pass


@pytest.mark.parametrize(
    ("dto", "return_dto"),
    [pytest.param(None, None, id="no-dto"), pytest.param(DataclassDTO[Model], None, id="data-dto-only")],
)
def test_direct_create_for_field_definition_serves_direction_the_plan_lacks(dto: Any, return_dto: Any) -> None:
    app = Litestar([make_handler(dto, return_dto)])
    handler: HTTPRouteHandler = app.route_handler_method_map["/"]["POST"]  # type: ignore[assignment]
    request = RequestFactory(app=app).post("/", route_handler=handler)
    return_field = FieldDefinition.from_annotation(Model)

    with pytest.warns(LitestarDeprecationWarning):
        OtherDTO.create_for_field_definition(return_field, handler_id=handler.handler_id)
        encoded = OtherDTO(request).data_to_encodable_type(Model(a=1, b="two"))
    schema = OtherDTO.create_openapi_schema(
        return_field, handler.handler_id, SchemaCreator(plugins=openapi_schema_plugins)
    )

    assert msgspec.to_builtins(encoded) == {"a": 1, "b": "two"}
    assert isinstance(schema, Reference)
    assert schema.ref.endswith("ModelResponseBody")


def test_direct_create_for_field_definition_serves_data_direction_the_plan_lacks() -> None:
    app = Litestar([make_handler(None, None)])
    handler: HTTPRouteHandler = app.route_handler_method_map["/"]["POST"]  # type: ignore[assignment]
    request = RequestFactory(app=app).post("/", route_handler=handler)

    with pytest.warns(LitestarDeprecationWarning):
        OtherDTO.create_for_field_definition(
            FieldDefinition.from_annotation(JSONBody[Model]), handler_id=handler.handler_id
        )
        assert OtherDTO(request).decode_bytes(PAYLOAD) == Model(a=1, b="two")
