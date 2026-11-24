from __future__ import annotations

import dataclasses
import gc
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from typing import Annotated, Any, Generic, Optional, TypeVar

import msgspec
import pytest

from litestar import Litestar, Response, get, post, websocket_listener
from litestar._openapi.schema_generation import SchemaCreator
from litestar._openapi.schema_generation.plugins import openapi_schema_plugins
from litestar.connection import ASGIConnection
from litestar.dto import AbstractDTO, DataclassDTO, DTOConfig
from litestar.dto._backend import DTOBackend
from litestar.dto._plan import build_dto_plan, build_schema_annotation, create_dto_openapi_schema
from litestar.enums import RequestEncodingType
from litestar.exceptions import (
    DTOFactoryException,
    LitestarException,
    LitestarWarning,
)
from litestar.handlers import HTTPRouteHandler, WebsocketListenerRouteHandler, websocket_stream
from litestar.openapi.spec import Reference
from litestar.params import BodyKwarg, JSONBody, MultipartBody, URLEncodedBody
from litestar.plugins import SerializationPlugin
from litestar.testing import RequestFactory, TestClient, create_test_client
from litestar.types import Empty
from litestar.typing import FieldDefinition
from tests.unit.test_dto import create_backend_for, registered

T = TypeVar("T")


@dataclass
class Model:
    a: int
    b: str


@dataclass
class OtherModel:
    a: int


@dataclass
class WithCount(Generic[T]):
    count: int
    data: list[T]


@dataclass
class PluginModel:
    a: int
    b: str


@dataclass
class Item:
    a: int
    secret: str = "hidden"


ModelDTO = DataclassDTO[Model]
ModelReadDTO = DataclassDTO[Annotated[Model, DTOConfig(exclude={"b"})]]
ItemDTO = DataclassDTO[Annotated[Item, DTOConfig(exclude={"secret"})]]


class CustomBackend(DTOBackend):
    __slots__ = ()


class StubPlugin(SerializationPlugin):
    def __init__(self, dto: type[AbstractDTO[Any]] | None = None) -> None:
        self.dto = dto or DataclassDTO[PluginModel]
        self.calls = 0

    def supports_type(self, field_definition: FieldDefinition) -> bool:
        return field_definition.is_subclass_of(PluginModel)

    def create_dto_for_type(self, field_definition: FieldDefinition) -> type[AbstractDTO[Any]]:
        self.calls += 1
        return self.dto


def make_rule_handler(dto: Any, return_dto: Any, body: Any, returns: Any) -> HTTPRouteHandler:
    namespace = {"_RuleBody": body, "_RuleReturn": returns}
    if body is None:

        async def no_body() -> _RuleReturn:  # type: ignore[name-defined]  # noqa: F821
            return None

        fn: Any = no_body
    else:

        async def with_body(data: JSONBody[_RuleBody]) -> _RuleReturn:  # type: ignore[name-defined]  # noqa: F821
            return None

        fn = with_body
    return post("/", dto=dto, return_dto=return_dto, signature_namespace=namespace)(fn)


def test_create_backend_data_direction() -> None:
    backend = create_backend_for(
        DataclassDTO[Model],
        FieldDefinition.from_annotation(JSONBody[Model]),
        is_data_field=True,
        handler_id="pkg.handler::1",
    )

    assert backend.is_data_field is True
    assert backend.transfer_model_type.__name__.endswith("RequestBody")
    assert backend.handler_id == "pkg.handler::1"


def test_create_backend_return_direction() -> None:
    backend = create_backend_for(
        DataclassDTO[Model], FieldDefinition.from_annotation(Model), is_data_field=False, handler_id="pkg.handler::1"
    )

    assert backend.is_data_field is False
    assert backend.transfer_model_type.__name__.endswith("ResponseBody")
    assert backend.handler_id == "pkg.handler::1"


def test_create_backend_generic_wrapper() -> None:
    backend = create_backend_for(
        DataclassDTO[Model],
        FieldDefinition.from_annotation(WithCount[Model]),
        is_data_field=False,
        handler_id="h",
    )

    assert backend.wrapper_attribute_name == "data"
    assert backend.field_definition.annotation == list[Model]


def test_create_backend_uses_backend_cls() -> None:
    backend = create_backend_for(
        DataclassDTO[Model],
        FieldDefinition.from_annotation(Model),
        is_data_field=False,
        handler_id="h",
        backend_cls=CustomBackend,
    )

    assert type(backend) is CustomBackend


@pytest.mark.parametrize(
    ("annotation", "expected"),
    [
        pytest.param(Model, lambda backend: backend.transfer_model_type, id="model"),
        pytest.param(list[Model], lambda backend: list[backend.transfer_model_type], id="list"),
        pytest.param(WithCount[Model], lambda backend: WithCount[backend.transfer_model_type], id="generic-wrapper"),
        pytest.param(Response[Model], lambda backend: backend.annotation, id="response"),
    ],
)
def test_build_schema_annotation(annotation: Any, expected: Callable[[DTOBackend], Any]) -> None:
    dto = DataclassDTO[Model]
    field_definition = FieldDefinition.from_annotation(annotation)
    backend = create_backend_for(dto, field_definition, is_data_field=False, handler_id="h")

    assert build_schema_annotation(dto, backend, field_definition) == expected(backend)


def test_build_schema_annotation_of_response_ignores_the_wrapper() -> None:
    dto = DataclassDTO[Model]
    field_definition = FieldDefinition.from_annotation(Response[Model])
    backend = create_backend_for(dto, field_definition, is_data_field=False, handler_id="h")

    assert backend.wrapper_attribute_name == "content"
    assert build_schema_annotation(dto, backend, field_definition) is backend.annotation


def test_registration_does_not_overwrite_configuration() -> None:
    plugin = StubPlugin()
    handler = registered(Litestar([make_rule_handler(Empty, Empty, PluginModel, PluginModel)], plugins=[plugin]))

    assert handler._dto is Empty
    assert handler._return_dto is Empty
    assert handler.data_dto is plugin.dto
    assert handler.return_dto is plugin.dto


def test_merge_of_registered_handler_keeps_configuration() -> None:
    plugin = StubPlugin()
    handler = registered(Litestar([make_rule_handler(Empty, Empty, PluginModel, PluginModel)], plugins=[plugin]))

    merged = handler.merge()

    assert merged._dto is Empty
    assert merged._return_dto is Empty
    assert merged._dto_plan is None


def test_dto_properties_of_unregistered_handler() -> None:
    configured = make_rule_handler(ModelDTO, ModelReadDTO, Model, Model)
    unconfigured = make_rule_handler(Empty, Empty, Model, Model)

    assert configured.data_dto is ModelDTO
    assert configured.return_dto is ModelReadDTO
    with pytest.raises(LitestarException):
        unconfigured.data_dto
    with pytest.raises(LitestarException):
        unconfigured.return_dto


def test_handler_on_several_paths_has_one_plan() -> None:
    @get(["/a", "/b"], return_dto=ModelReadDTO)
    async def handler() -> Model:
        return Model(a=1, b="two")

    with create_test_client([handler]) as client:
        handler_a = registered(client.app, "/a", "GET")
        assert handler_a is registered(client.app, "/b", "GET")
        assert handler_a._dto_plan is not None
        assert client.get("/a").json() == {"a": 1}
        assert client.get("/b").json() == {"a": 1}


def test_two_apps_build_independent_plans() -> None:
    @get("/", return_dto=ModelReadDTO)
    async def handler() -> Model:
        return Model(a=1, b="two")

    first = registered(Litestar([handler]), method="GET")
    second = registered(Litestar([handler]), method="GET")

    assert first is not second
    assert first._dto_plan.return_.backend is not second._dto_plan.return_.backend
    assert handler._dto_plan is None


def test_build_dto_plan_is_idempotent() -> None:
    app = Litestar([make_rule_handler(ModelDTO, ModelReadDTO, Model, Model)])
    handler = registered(app)
    plan = handler._dto_plan

    first = build_dto_plan(handler, app)
    second = build_dto_plan(handler, app)

    assert first.data_dto is second.data_dto is ModelDTO
    assert first.data is not None and second.data is not None
    assert first.return_ is not None and second.return_ is not None
    assert first.data.dto is second.data.dto
    assert first.return_.dto is second.return_.dto
    assert first.data.backend is not second.data.backend
    assert first.return_.backend is not second.return_.backend
    assert handler._dto is ModelDTO
    assert handler._return_dto is ModelReadDTO
    assert handler._dto_plan is plan


def test_second_on_registration_rebuilds_plan() -> None:
    plugin = StubPlugin()

    @post("/")
    async def handler(data: JSONBody[PluginModel]) -> PluginModel:
        return data

    with create_test_client([handler], plugins=[plugin]) as client:
        registered_handler = registered(client.app)
        plan = registered_handler._dto_plan
        calls = plugin.calls
        route = next(route for route in client.app.routes if route.path == "/")

        registered_handler.on_registration(route, client.app)

        assert registered_handler._dto_plan is not plan
        assert registered_handler._dto is Empty
        assert plugin.calls > calls
        assert client.post("/", json={"a": 1, "b": "two"}).status_code == 201


def test_app_register_plans_new_handler() -> None:
    @post("/")
    async def handler(data: JSONBody[Model]) -> Model:
        return data

    @post("/extra", dto=ModelDTO, return_dto=ModelReadDTO)
    async def extra(data: JSONBody[Model]) -> Model:
        return data

    app = Litestar([handler], dto=ModelDTO)
    old = registered(app)
    old_plan = old._dto_plan
    with pytest.warns(LitestarWarning):
        app.register(extra)

    assert registered(app, "/extra")._dto_plan is not None
    assert old._dto_plan is old_plan
    with TestClient(app) as client:
        assert client.post("/", json={"a": 1, "b": "two"}).json() == {"a": 1, "b": "two"}
        assert client.post("/extra", json={"a": 1, "b": "two"}).json() == {"a": 1}


def test_equal_handler_ids_do_not_share_backends(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("litestar.handlers.base.id", lambda _: 0, raising=False)

    def make(forbid_unknown_fields: bool) -> HTTPRouteHandler:
        dto = DataclassDTO[Annotated[Model, DTOConfig(forbid_unknown_fields=forbid_unknown_fields)]]

        @post("/", dto=dto, return_dto=None)
        async def handler(data: JSONBody[Model]) -> None:
            return None

        return handler

    first, second = Litestar([make(False)]), Litestar([make(True)])
    assert registered(first).handler_id == registered(second).handler_id

    payload = {"a": 1, "b": "two", "unknown": 3}
    with TestClient(first) as client:
        assert client.post("/", json=payload).status_code == 201
    with TestClient(second) as client:
        assert client.post("/", json=payload).status_code == 400


def test_listener_data_field_has_no_body_marker() -> None:
    @websocket_listener("/ws", dto=ItemDTO)
    async def handler(data: Item) -> Item:
        return data

    with create_test_client([handler]) as client:
        listener = registered(client.app, "/ws", "websocket")
        assert isinstance(listener, WebsocketListenerRouteHandler)
        assert listener.parsed_data_field is not None
        assert not isinstance(listener.parsed_data_field.kwarg_definition, BodyKwarg)
        assert listener._dto_plan is not None
        assert listener._dto_plan.data is not None
        assert listener._dto_plan.data.backend.transfer_model_type.__name__.endswith("RequestBody")
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"a": 1, "secret": "sent"})
            assert ws.receive_json() == {"a": 1}


def test_stream_resolves_dtos_once() -> None:
    plugin = StubPlugin(DataclassDTO[Annotated[PluginModel, DTOConfig(exclude={"b"})]])

    @websocket_stream("/stream")
    async def handler() -> AsyncGenerator[PluginModel, None]:
        yield PluginModel(a=1, b="two")

    with create_test_client([handler], plugins=[plugin]) as client:
        assert plugin.calls == 1
        with client.websocket_connect("/stream") as ws:
            assert ws.receive_json() == {"a": 1}


def openapi_ref(dto: type[AbstractDTO[Any]], field_definition: FieldDefinition | None, handler_id: str) -> str:
    assert field_definition is not None
    schema_creator = SchemaCreator(plugins=openapi_schema_plugins)
    result = dto.create_openapi_schema(
        field_definition=field_definition, handler_id=handler_id, schema_creator=schema_creator
    )
    schema_creator.schema_registry.generate_components_schemas()
    assert isinstance(result, Reference)
    return result.ref


def _operation_refs(app: Litestar) -> tuple[str, str]:
    operation = app.openapi_schema.paths["/"].post  # type: ignore[index, union-attr]
    request_ref = operation.request_body.content["application/json"].schema.ref  # type: ignore[union-attr]
    response_ref = operation.responses["201"].content["application/json"].schema.ref  # type: ignore[union-attr, index]
    return request_ref, response_ref


def test_create_openapi_schema_with_handler_id() -> None:
    app = Litestar([make_rule_handler(ModelDTO, ModelReadDTO, Model, Model)])
    handler = registered(app)
    request_ref, response_ref = _operation_refs(app)

    assert openapi_ref(ModelReadDTO, handler.parsed_fn_signature.return_type, handler.handler_id) == response_ref
    assert openapi_ref(ModelDTO, handler.parsed_data_field, handler.handler_id) == request_ref


@pytest.mark.parametrize(
    "field_name",
    [
        pytest.param("parsed_data_field", id="data-field"),
        pytest.param("return_type", id="signature-return-type"),
        pytest.param("parsed_return_field", id="parsed-return-field"),
    ],
)
def test_create_openapi_schema_same_model_in_both_directions(field_name: str) -> None:
    data_dto = DataclassDTO[Annotated[Model, DTOConfig(exclude={"a"})]]
    return_dto = DataclassDTO[Annotated[Model, DTOConfig(exclude={"b"})]]
    app = Litestar([make_rule_handler(data_dto, return_dto, Model, Model)])
    handler = registered(app)
    request_ref, response_ref = _operation_refs(app)
    components = app.openapi_schema.components.schemas
    field_definition = (
        handler.parsed_fn_signature.return_type if field_name == "return_type" else getattr(handler, field_name)
    )
    is_data_field = field_name == "parsed_data_field"

    assert field_definition == handler.parsed_data_field
    ref = openapi_ref(data_dto if is_data_field else return_dto, field_definition, handler.handler_id)

    assert ref == (request_ref if is_data_field else response_ref)
    name = ref.rsplit("/", 1)[1]
    assert name.endswith("RequestBody" if is_data_field else "ResponseBody")
    assert set(components[name].properties) == ({"b"} if is_data_field else {"a"})  # type: ignore[arg-type]


def test_create_openapi_schema_for_listener_data_field() -> None:
    @websocket_listener("/ws", dto=ItemDTO)
    async def handler(data: Item) -> None:
        return None

    listener = registered(Litestar([handler]), "/ws", "websocket")

    assert openapi_ref(ItemDTO, listener.parsed_data_field, listener.handler_id).endswith("ItemRequestBody")


def test_create_openapi_schema_for_copy_of_listener_data_field_is_return_direction() -> None:
    @websocket_listener("/ws", dto=ItemDTO)
    async def handler(data: Item) -> Item:
        return data

    listener = registered(Litestar([handler]), "/ws", "websocket")
    copied_field = dataclasses.replace(listener.parsed_data_field)

    assert openapi_ref(ItemDTO, copied_field, listener.handler_id).endswith("ItemResponseBody")


def test_create_openapi_schema_finds_a_live_handler_by_a_copy_of_its_id() -> None:
    app = Litestar([make_rule_handler(ModelDTO, None, Model, None)])
    handler = registered(app)
    field_definition = handler.parsed_data_field
    handler_id = f"{handler.handler_id}"

    assert openapi_ref(ModelDTO, field_definition, handler_id).endswith("ModelRequestBody")

    del app, handler
    gc.collect()
    with pytest.raises(DTOFactoryException):
        ModelDTO.create_openapi_schema(field_definition, handler_id, SchemaCreator())


class NoInstanceDTO(DataclassDTO[Model]):
    def __init__(self, asgi_connection: ASGIConnection[Any, Any, Any, Any]) -> None:
        raise AssertionError("a stock DTO must not be instantiated per request")


def test_stock_dto_is_not_instantiated_per_request() -> None:
    @post("/json", dto=NoInstanceDTO)
    async def json_handler(data: JSONBody[Model]) -> Model:
        return data

    @post("/form", dto=NoInstanceDTO)
    async def form_handler(data: URLEncodedBody[Model]) -> Model:
        return data

    @websocket_listener("/ws", dto=NoInstanceDTO)
    async def listener(data: Model) -> Model:
        return data

    @websocket_stream("/stream", return_dto=NoInstanceDTO)
    async def stream() -> AsyncGenerator[Model, None]:
        yield Model(a=1, b="two")

    with create_test_client([json_handler, form_handler, listener, stream]) as client:
        assert client.post("/json", json={"a": 1, "b": "two"}).json() == {"a": 1, "b": "two"}
        assert client.post("/form", data={"a": "1", "b": "two"}).json() == {"a": 1, "b": "two"}
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"a": 1, "b": "two"})
            assert ws.receive_json() == {"a": 1, "b": "two"}
        with client.websocket_connect("/stream") as ws:
            assert ws.receive_json() == {"a": 1, "b": "two"}


class Custom:
    def __init__(self, value: str) -> None:
        self.value = value


@dataclass
class CustomHolder:
    custom: Custom


CUSTOM_DECODERS = [(lambda target: target is Custom, lambda target, value: Custom(value))]


def test_type_decoders_are_bound_at_build() -> None:
    @post("/", dto=DataclassDTO[CustomHolder], return_dto=None, type_decoders=CUSTOM_DECODERS)
    async def handler(data: JSONBody[CustomHolder]) -> str:
        return data.custom.value

    @post("/other")
    async def other(data: JSONBody[dict[str, Any]]) -> None:
        return None

    with create_test_client([handler]) as client:
        assert client.post("/", json={"custom": "x"}).text == "x"
        plan = registered(client.app)._dto_plan
    connection_of_other_handler = RequestFactory().post("/other", route_handler=other)

    assert plan.decode_bytes(b'{"custom": "y"}', connection_of_other_handler).custom.value == "y"
    assert plan.decode_builtins({"custom": "z"}, connection_of_other_handler).custom.value == "z"


class OwnInitBackend(DTOBackend):
    __slots__ = ()

    def __init__(
        self,
        dto_factory: type[AbstractDTO[Any]],
        field_definition: FieldDefinition,
        handler_id: str,
        is_data_field: bool,
        model_type: type[Any],
        wrapper_attribute_name: str | None,
    ) -> None:
        self.annotation = CustomHolder


@pytest.mark.parametrize("backend_kind", ["base-init", "own-init"])
def test_unbound_backend_reads_the_connection(backend_kind: str) -> None:
    @post("/", type_decoders=CUSTOM_DECODERS)
    async def handler(data: JSONBody[CustomHolder]) -> None:
        return None

    dto = DataclassDTO[CustomHolder]
    field_definition = FieldDefinition.from_annotation(JSONBody[CustomHolder])
    if backend_kind == "base-init":
        backend = create_backend_for(dto, field_definition, is_data_field=True, handler_id="h")
    else:
        backend = OwnInitBackend(
            dto_factory=dto,
            field_definition=field_definition,
            handler_id="h",
            is_data_field=True,
            model_type=CustomHolder,
            wrapper_attribute_name=None,
        )
    request = RequestFactory().post("/", route_handler=handler)

    assert backend.parse_raw(b'{"custom": "x"}', request).custom.value == "x"  # type: ignore[union-attr]
    assert backend.parse_builtins({"custom": "y"}, request).custom.value == "y"


def test_content_type_selects_msgpack_per_request() -> None:
    @post("/", dto=ModelDTO)
    async def handler(data: JSONBody[Model]) -> Model:
        return data

    with create_test_client([handler]) as client:
        json_response = client.post("/", json={"a": 1, "b": "two"})
        msgpack_response = client.post(
            "/",
            content=msgspec.msgpack.encode({"a": 1, "b": "two"}),
            headers={"content-type": RequestEncodingType.MESSAGEPACK},
        )

    assert (json_response.status_code, json_response.json()) == (201, {"a": 1, "b": "two"})
    assert (msgpack_response.status_code, msgpack_response.json()) == (201, {"a": 1, "b": "two"})


def test_form_bodies_decode_through_the_plan() -> None:
    @post("/url-encoded", dto=ItemDTO, return_dto=None)
    async def url_encoded(data: URLEncodedBody[Item]) -> dict[str, Any]:
        return {"a": data.a, "secret": data.secret}

    @post("/multipart", dto=ItemDTO, return_dto=None)
    async def multipart(data: MultipartBody[Item]) -> dict[str, Any]:
        return {"a": data.a, "secret": data.secret}

    with create_test_client([url_encoded, multipart]) as client:
        form = {"a": "1", "secret": "sent"}
        assert client.post("/url-encoded", data=form).json() == {"a": 1, "secret": "hidden"}
        response = client.post("/multipart", data=form, files={"upload": ("f.txt", b"x")})
        assert response.json() == {"a": 1, "secret": "hidden"}


async def test_to_response_on_unregistered_handler_raises() -> None:
    @get("/")
    async def handler() -> Model:
        return Model(a=1, b="two")

    with pytest.raises(LitestarException):
        await handler.to_response(Model(a=1, b="two"), RequestFactory().get("/", route_handler=handler))


@pytest.mark.parametrize(
    ("is_data_field", "annotation"),
    [
        pytest.param(True, Model, id="data-model"),
        pytest.param(True, list[Model], id="data-list"),
        pytest.param(True, Optional[Model], id="data-optional"),
        pytest.param(False, Model, id="return-model"),
        pytest.param(False, list[Model], id="return-list"),
        pytest.param(False, Optional[Model], id="return-optional"),
        pytest.param(False, WithCount[Model], id="return-generic-wrapper"),
        pytest.param(False, Response[Model], id="return-response"),
    ],
)
def test_plan_schema_matches_create_openapi_schema(is_data_field: bool, annotation: Any) -> None:
    if is_data_field:
        handler_fn = make_rule_handler(ModelDTO, None, annotation, None)
    else:
        handler_fn = make_rule_handler(Empty, ModelDTO, None, annotation)
    handler = registered(Litestar([handler_fn]))
    plan = handler._dto_plan
    direction_plan = plan.data if is_data_field else plan.return_
    field_definition = handler.parsed_data_field if is_data_field else handler.parsed_fn_signature.return_type
    assert direction_plan is not None

    plan_creator = SchemaCreator(plugins=openapi_schema_plugins)
    shim_creator = SchemaCreator(plugins=openapi_schema_plugins)
    from_plan = create_dto_openapi_schema(direction_plan, field_definition, handler, plan_creator)
    from_shim = ModelDTO.create_openapi_schema(
        field_definition=field_definition, handler_id=handler.handler_id, schema_creator=shim_creator
    )

    assert from_plan == from_shim
    assert (
        plan_creator.schema_registry.generate_components_schemas()
        == shim_creator.schema_registry.generate_components_schemas()
    )


def test_openapi_generation_does_not_call_create_openapi_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(cls: Any, field_definition: FieldDefinition, handler_id: str, schema_creator: SchemaCreator) -> Any:
        raise AssertionError("OpenAPI generation must read the plan")

    monkeypatch.setattr(AbstractDTO, "create_openapi_schema", classmethod(fail))
    app = Litestar([make_rule_handler(ModelDTO, ModelReadDTO, Model, Model)])

    names = list(app.openapi_schema.components.schemas)

    assert sum(name.endswith("ModelRequestBody") for name in names) == 1
    assert sum(name.endswith("ModelResponseBody") for name in names) == 1


def test_unregistered_listener_without_dto_resolves_its_handlers() -> None:
    @websocket_listener("/ws", dto=None, return_dto=None)
    async def without_dto(data: str) -> str:
        return data

    @websocket_listener("/ws", dto=ItemDTO)
    async def with_dto(data: Item) -> Item:
        return data

    assert callable(without_dto.resolve_receive_handler())
    assert callable(without_dto.resolve_send_handler())
    with pytest.raises(LitestarException):
        with_dto.resolve_receive_handler()
    with pytest.raises(LitestarException):
        with_dto.resolve_send_handler()
