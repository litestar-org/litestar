import copy
import dataclasses
import json
import pickle
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from typing import Annotated, Any, ClassVar, Generic, TypeVar

import msgspec
import pytest

from litestar import Controller, Litestar, Response, get, post, websocket_listener
from litestar._openapi.schema_generation import SchemaCreator
from litestar._openapi.schema_generation.plugins import openapi_schema_plugins
from litestar.connection import ASGIConnection
from litestar.dto import AbstractDTO, DataclassDTO, DTOConfig
from litestar.dto._backend import DTOBackend
from litestar.dto._plan import (
    DTODirectionPlan,
    DTOPlan,
    _plan_build,
    build_dto_plan,
    build_schema_annotation,
    create_backend,
)
from litestar.enums import RequestEncodingType
from litestar.exceptions import DTOFactoryException, InvalidAnnotationException, LitestarException, LitestarWarning
from litestar.handlers import BaseRouteHandler, HTTPRouteHandler, WebsocketListenerRouteHandler, websocket_stream
from litestar.openapi.spec import Reference
from litestar.params import BodyKwarg, JSONBody, MultipartBody, URLEncodedBody
from litestar.plugins import SerializationPlugin
from litestar.serialization import encode_json
from litestar.testing import RequestFactory, TestClient, create_test_client
from litestar.types import Empty, Method
from litestar.typing import FieldDefinition

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

        async def no_body() -> "_RuleReturn":  # type: ignore[name-defined]  # noqa: F821
            return None

        fn: Any = no_body
    else:

        async def with_body(data: "JSONBody[_RuleBody]") -> "_RuleReturn":  # type: ignore[name-defined]  # noqa: F821
            return None

        fn = with_body
    return post("/", dto=dto, return_dto=return_dto, signature_namespace=namespace)(fn)


def registered(app: Litestar, path: str = "/", method: Method = "POST") -> Any:
    return app.route_handler_method_map[path][method]


def websocket_handler(app: Litestar, path: str) -> Any:
    return app.route_handler_method_map[path]["websocket"]


def test_create_backend_data_direction() -> None:
    backend = create_backend(
        DataclassDTO[Model],
        FieldDefinition.from_annotation(JSONBody[Model]),
        is_data_field=True,
        handler_id="pkg.handler::1",
    )

    assert backend.is_data_field is True
    assert backend.transfer_model_type.__name__.endswith("RequestBody")
    assert backend.handler_id == "pkg.handler::1"


def test_create_backend_return_direction() -> None:
    backend = create_backend(
        DataclassDTO[Model], FieldDefinition.from_annotation(Model), is_data_field=False, handler_id="pkg.handler::1"
    )

    assert backend.is_data_field is False
    assert backend.transfer_model_type.__name__.endswith("ResponseBody")
    assert backend.handler_id == "pkg.handler::1"


def test_create_backend_raises_for_mismatched_model() -> None:
    with pytest.raises(InvalidAnnotationException, match="DTO narrowed with"):
        create_backend(
            DataclassDTO[Model], FieldDefinition.from_annotation(OtherModel), is_data_field=False, handler_id="h"
        )


def test_create_backend_raises_for_non_homogeneous_tuple() -> None:
    with pytest.raises(InvalidAnnotationException, match="DTO narrowed with"):
        create_backend(
            DataclassDTO[Model],
            FieldDefinition.from_annotation(tuple[Model, str]),
            is_data_field=False,
            handler_id="h",
        )


def test_create_backend_generic_wrapper() -> None:
    backend = create_backend(
        DataclassDTO[Model],
        FieldDefinition.from_annotation(WithCount[Model]),
        is_data_field=False,
        handler_id="h",
    )

    assert backend.wrapper_attribute_name == "data"
    assert backend.field_definition.annotation == list[Model]


def test_create_backend_uses_backend_cls() -> None:
    class CustomBackend(DTOBackend):
        __slots__ = ()

    backend = create_backend(
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
    backend = create_backend(dto, field_definition, is_data_field=False, handler_id="h")

    assert build_schema_annotation(dto, backend, field_definition) == expected(backend)


def test_build_schema_annotation_of_response_ignores_the_wrapper() -> None:
    dto = DataclassDTO[Model]
    field_definition = FieldDefinition.from_annotation(Response[Model])
    backend = create_backend(dto, field_definition, is_data_field=False, handler_id="h")

    assert backend.wrapper_attribute_name == "content"
    assert build_schema_annotation(dto, backend, field_definition) is backend.annotation


def test_plan_types_are_frozen() -> None:
    dto = DataclassDTO[Model]
    backend = create_backend(dto, FieldDefinition.from_annotation(Model), is_data_field=False, handler_id="h")
    direction = DTODirectionPlan(dto=dto, backend=backend, schema_annotation=backend.annotation)
    plan = DTOPlan(data=None, return_=direction, data_dto=None)

    with pytest.raises(dataclasses.FrozenInstanceError):
        direction.backend = backend  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        plan.data_dto = dto  # type: ignore[misc]


@pytest.mark.parametrize(
    ("dto", "body", "expected", "has_data"),
    [
        pytest.param(ModelDTO, Model, ModelDTO, True, id="D1"),
        pytest.param(ModelDTO, None, ModelDTO, False, id="D3"),
        pytest.param(None, PluginModel, None, False, id="D4"),
        pytest.param(Empty, PluginModel, "plugin", True, id="D5"),
        pytest.param(Empty, Model, None, False, id="D6"),
        pytest.param(Empty, None, None, False, id="D7"),
    ],
)
def test_data_resolution_rules(dto: Any, body: Any, expected: Any, has_data: bool) -> None:
    plugin = StubPlugin()
    app = Litestar([make_rule_handler(dto, None, body, None)], plugins=[plugin])
    handler = registered(app)

    assert handler.data_dto is (plugin.dto if expected == "plugin" else expected)
    assert (handler._dto_plan.data is not None) is has_data


def test_handler_data_dto_that_cannot_apply_raises() -> None:
    with pytest.raises(InvalidAnnotationException):
        Litestar([make_rule_handler(ModelDTO, None, dict[str, Any], None)])


def test_layer_data_dto_that_cannot_apply_raises() -> None:
    class MyController(Controller):
        path = "/"
        dto = ModelDTO

        @post()
        async def handler(self, data: JSONBody[dict[str, Any]]) -> None:
            return None

    with pytest.raises(InvalidAnnotationException):
        Litestar([MyController])


@pytest.mark.parametrize(
    ("dto", "return_dto", "body", "returns", "expected"),
    [
        pytest.param(Empty, ModelReadDTO, None, Model, ModelReadDTO, id="R1-type"),
        pytest.param(ModelDTO, None, Model, Model, None, id="R1-none"),
        pytest.param(ModelDTO, Empty, Model, Model, ModelDTO, id="R2"),
        pytest.param(Empty, Empty, None, PluginModel, "plugin", id="R3"),
        pytest.param(DataclassDTO[PluginModel], Empty, PluginModel, PluginModel, "explicit", id="R2-before-R3"),
        pytest.param(ModelDTO, Empty, Model, OtherModel, None, id="R4"),
    ],
)
def test_return_resolution_rules(dto: Any, return_dto: Any, body: Any, returns: Any, expected: Any) -> None:
    plugin = StubPlugin()
    app = Litestar([make_rule_handler(dto, return_dto, body, returns)], plugins=[plugin])
    handler = registered(app)

    if expected == "plugin":
        assert handler.return_dto is plugin.dto
    elif expected == "explicit":
        assert handler.return_dto is dto
        assert handler.return_dto is not plugin.dto
    else:
        assert handler.return_dto is expected


def test_return_dto_without_wrapper_match_raises() -> None:
    with pytest.raises(InvalidAnnotationException):
        Litestar([make_rule_handler(Empty, ModelDTO, None, tuple[Model, str])])


def test_handler_return_dto_that_cannot_apply_is_dropped() -> None:
    @post("/", return_dto=ModelReadDTO)
    async def handler(data: JSONBody[dict[str, Any]]) -> dict[str, Any]:
        return data

    with create_test_client([handler]) as client:
        registered_handler = registered(client.app)
        assert registered_handler.return_dto is None
        assert registered_handler._return_dto is ModelReadDTO
        response = client.post("/", json={"a": 1, "b": "two"})
        assert response.json() == {"a": 1, "b": "two"}


def test_layer_return_dto_that_cannot_apply_is_dropped() -> None:
    class MyController(Controller):
        path = "/"
        return_dto = ModelReadDTO

        @get()
        async def handler(self) -> dict[str, Any]:
            return {}

    assert registered(Litestar([MyController]), method="GET").return_dto is None


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
        listener = websocket_handler(client.app, "/ws")
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


class CustomBackend(DTOBackend):
    __slots__ = ()


def test_backend_cls_through_create_for_field_definition_override() -> None:
    class OverridingDTO(DataclassDTO[Model]):
        @classmethod
        def create_for_field_definition(
            cls, field_definition: FieldDefinition, handler_id: str, backend_cls: type[DTOBackend] | None = None
        ) -> None:
            super().create_for_field_definition(
                field_definition=field_definition, handler_id=handler_id, backend_cls=CustomBackend
            )

    @post("/", dto=OverridingDTO, return_dto=None)
    async def handler(data: JSONBody[Model]) -> Model:
        return data

    with create_test_client([handler]) as client:
        assert type(registered(client.app)._dto_plan.data.backend) is CustomBackend
        response = client.post("/", json={"a": 1, "b": "two"})
        assert response.status_code == 201
        assert response.json() == {"a": 1, "b": "two"}


def test_create_for_field_definition_override_without_backend_raises() -> None:
    class SilentDTO(DataclassDTO[Model]):
        @classmethod
        def create_for_field_definition(
            cls, field_definition: FieldDefinition, handler_id: str, backend_cls: type[DTOBackend] | None = None
        ) -> None:
            return None

    with pytest.raises(DTOFactoryException):
        Litestar([make_rule_handler(SilentDTO, None, Model, None)])


def test_nested_create_for_field_definition_does_not_inherit_plan_build() -> None:
    class OtherDTO(DataclassDTO[OtherModel]):
        pass

    class NestingDTO(DataclassDTO[Model]):
        @classmethod
        def create_for_field_definition(
            cls, field_definition: FieldDefinition, handler_id: str, backend_cls: type[DTOBackend] | None = None
        ) -> None:
            OtherDTO.create_for_field_definition(FieldDefinition.from_annotation(OtherModel), handler_id="other")
            super().create_for_field_definition(field_definition=field_definition, handler_id=handler_id)
            super().create_for_field_definition(
                field_definition=field_definition, handler_id=handler_id, backend_cls=CustomBackend
            )

    handler = registered(Litestar([make_rule_handler(NestingDTO, None, Model, None)]))
    direction = handler._dto_plan.data

    assert direction.dto is NestingDTO
    assert direction.backend.dto_factory is NestingDTO
    assert direction.backend.is_data_field is True
    assert type(direction.backend) is DTOBackend
    assert _plan_build.get() is None


def openapi_ref(dto: type[AbstractDTO[Any]], field_definition: FieldDefinition | None, handler_id: str) -> str:
    assert field_definition is not None
    schema_creator = SchemaCreator(plugins=openapi_schema_plugins)
    result = dto.create_openapi_schema(
        field_definition=field_definition, handler_id=handler_id, schema_creator=schema_creator
    )
    schema_creator.schema_registry.generate_components_schemas()
    assert isinstance(result, Reference)
    return result.ref


def test_direct_create_for_field_definition_then_shims() -> None:
    dto = DataclassDTO[Model]
    field_definition = FieldDefinition.from_annotation(JSONBody[Model])

    dto.create_for_field_definition(field_definition, handler_id="direct")

    assert openapi_ref(dto, field_definition, "direct").endswith("ModelRequestBody")


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


def test_create_openapi_schema_same_model_in_both_directions() -> None:
    data_dto = DataclassDTO[Annotated[Model, DTOConfig(exclude={"a"})]]
    return_dto = DataclassDTO[Annotated[Model, DTOConfig(exclude={"b"})]]
    app = Litestar([make_rule_handler(data_dto, return_dto, Model, Model)])
    handler = registered(app)
    request_ref, response_ref = _operation_refs(app)
    components = app.openapi_schema.components.schemas

    for return_field in (handler.parsed_fn_signature.return_type, handler.parsed_return_field):
        assert return_field == handler.parsed_data_field
        assert openapi_ref(return_dto, return_field, handler.handler_id) == response_ref
    assert openapi_ref(data_dto, handler.parsed_data_field, handler.handler_id) == request_ref

    response_name, request_name = response_ref.rsplit("/", 1)[1], request_ref.rsplit("/", 1)[1]
    assert response_name.endswith("ResponseBody")
    assert request_name.endswith("RequestBody")
    assert set(components[response_name].properties) == {"a"}  # type: ignore[arg-type]
    assert set(components[request_name].properties) == {"b"}  # type: ignore[arg-type]


def test_create_openapi_schema_for_listener_data_field() -> None:
    @websocket_listener("/ws", dto=ItemDTO)
    async def handler(data: Item) -> None:
        return None

    listener = websocket_handler(Litestar([handler]), "/ws")

    assert openapi_ref(ItemDTO, listener.parsed_data_field, listener.handler_id).endswith("ItemRequestBody")


def test_handler_id_behaves_like_str() -> None:
    handler = registered(Litestar([make_rule_handler(ModelDTO, None, Model, None)]))
    handler_id = handler.handler_id

    assert handler_id == str(handler_id)
    assert hash(handler_id) == hash(str(handler_id))
    assert handler_id.split("::")[0] == str(handler)
    assert sorted([handler_id, "a", "zzz"]) == ["a", str(handler_id), "zzz"]
    assert type(copy.deepcopy(handler_id)) is str
    assert type(pickle.loads(pickle.dumps(handler_id))) is str
    assert json.dumps(handler_id) == f'"{handler_id}"'
    assert encode_json(handler_id) == f'"{handler_id}"'.encode()
    assert handler_id.handler is handler


@pytest.mark.parametrize(
    "copy_id",
    [pytest.param(str, id="str"), pytest.param(lambda handler_id: f"{handler_id}", id="f-string")],
)
def test_create_openapi_schema_with_plain_string_raises(copy_id: Callable[[str], str]) -> None:
    handler: BaseRouteHandler = registered(Litestar([make_rule_handler(ModelDTO, None, Model, None)]))

    with pytest.raises(DTOFactoryException):
        ModelDTO.create_openapi_schema(
            field_definition=handler.parsed_data_field,  # type: ignore[arg-type]
            handler_id=copy_id(handler.handler_id),
            schema_creator=SchemaCreator(),
        )


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


class DecodeBytesDTO(DataclassDTO[Model]):
    calls: ClassVar[list[str]] = []

    def decode_bytes(self, value: bytes) -> Any:
        self.calls.append("decode_bytes")
        return super().decode_bytes(value)


class DecodeBuiltinsDTO(DataclassDTO[Model]):
    calls: ClassVar[list[str]] = []

    def decode_builtins(self, value: dict[str, Any]) -> Any:
        self.calls.append("decode_builtins")
        return super().decode_builtins(value)


class EncodeDTO(DataclassDTO[Model]):
    calls: ClassVar[list[str]] = []

    def data_to_encodable_type(self, data: Any) -> Any:
        self.calls.append("data_to_encodable_type")
        return super().data_to_encodable_type(data)


def make_echo_app(dto: type[AbstractDTO[Any]]) -> Litestar:
    @post("/json", dto=dto)
    async def json_handler(data: JSONBody[Model]) -> Model:
        return data

    @post("/form", dto=dto)
    async def form_handler(data: URLEncodedBody[Model]) -> Model:
        return data

    return Litestar([json_handler, form_handler])


@pytest.mark.parametrize(
    ("dto", "path", "method"),
    [
        pytest.param(DecodeBytesDTO, "/json", "decode_bytes", id="decode_bytes"),
        pytest.param(DecodeBuiltinsDTO, "/form", "decode_builtins", id="decode_builtins"),
        pytest.param(EncodeDTO, "/json", "data_to_encodable_type", id="data_to_encodable_type"),
    ],
)
def test_overridden_instance_method_is_called(dto: Any, path: str, method: str) -> None:
    dto.calls.clear()
    kwargs: dict[str, Any] = {"json": {"a": 1, "b": "two"}} if path == "/json" else {"data": {"a": "1", "b": "two"}}

    with TestClient(make_echo_app(ModelDTO)) as client:
        stock = client.post(path, **kwargs)
    with TestClient(make_echo_app(dto)) as client:
        response = client.post(path, **kwargs)

    assert dto.calls == [method]
    assert (response.status_code, response.json()) == (stock.status_code, stock.json())


def test_only_the_overridden_method_goes_through_an_instance() -> None:
    instances: list[AbstractDTO[Any]] = []

    class CountingDTO(DataclassDTO[Model]):
        def __init__(self, asgi_connection: ASGIConnection[Any, Any, Any, Any]) -> None:
            instances.append(self)
            super().__init__(asgi_connection)

        def decode_bytes(self, value: bytes) -> Any:
            return super().decode_bytes(value)

    with TestClient(make_echo_app(CountingDTO)) as client:
        assert client.post("/json", json={"a": 1, "b": "two"}).json() == {"a": 1, "b": "two"}
        assert len(instances) == 1
        assert client.post("/form", data={"a": "1", "b": "two"}).json() == {"a": 1, "b": "two"}
        assert len(instances) == 1


@pytest.mark.parametrize(
    ("dto", "return_dto", "body", "returns"),
    [
        pytest.param(ModelDTO, Empty, Model, Model, id="both"),
        pytest.param(ModelDTO, None, Model, Model, id="data-only"),
        pytest.param(Empty, ModelReadDTO, None, Model, id="return-only"),
        pytest.param(ModelDTO, Empty, None, None, id="neither"),
    ],
)
def test_plan_callables_match_directions(dto: Any, return_dto: Any, body: Any, returns: Any) -> None:
    plan = registered(Litestar([make_rule_handler(dto, return_dto, body, returns)]))._dto_plan

    assert (plan.decode_bytes is not None) is (plan.data is not None)
    assert (plan.decode_builtins is not None) is (plan.data is not None)
    assert (plan.encode is not None) is (plan.return_ is not None)


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

    with create_test_client([handler]) as client:
        registered_handler = registered(client.app)
        assert registered_handler._dto_plan.data.backend._type_decoders is registered_handler.type_decoders
        assert client.post("/", json={"custom": "x"}).text == "x"


def test_unbound_backend_reads_the_connection() -> None:
    @post("/", type_decoders=CUSTOM_DECODERS)
    async def handler(data: JSONBody[CustomHolder]) -> None:
        return None

    field_definition = FieldDefinition.from_annotation(JSONBody[CustomHolder])
    backend = create_backend(DataclassDTO[CustomHolder], field_definition, is_data_field=True, handler_id="h")
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


class RecordingBackend(DTOBackend):
    __slots__ = ()
    calls: ClassVar[list[tuple[str, Any]]] = []

    def populate_data_from_raw(self, raw: bytes, asgi_connection: ASGIConnection[Any, Any, Any, Any]) -> Any:
        self.calls.append(("populate_data_from_raw", raw))
        return super().populate_data_from_raw(raw, asgi_connection)

    def encode_data(self, data: Any) -> Any:
        self.calls.append(("encode_data", data))
        return super().encode_data(data)


def test_backend_subclass_runtime_overrides_are_called() -> None:
    class RecordingBackendDTO(DataclassDTO[Model]):
        @classmethod
        def create_for_field_definition(
            cls, field_definition: FieldDefinition, handler_id: str, backend_cls: type[DTOBackend] | None = None
        ) -> None:
            super().create_for_field_definition(
                field_definition=field_definition, handler_id=handler_id, backend_cls=RecordingBackend
            )

    @post("/", dto=RecordingBackendDTO)
    async def handler(data: JSONBody[Model]) -> Model:
        return data

    RecordingBackend.calls.clear()
    with create_test_client([handler]) as client:
        response = client.post("/", content=b'{"a":1,"b":"two"}', headers={"content-type": "application/json"})

    assert response.json() == {"a": 1, "b": "two"}
    assert RecordingBackend.calls == [
        ("populate_data_from_raw", b'{"a":1,"b":"two"}'),
        ("encode_data", Model(a=1, b="two")),
    ]


async def test_to_response_on_unregistered_handler_raises() -> None:
    @get("/")
    async def handler() -> Model:
        return Model(a=1, b="two")

    with pytest.raises(LitestarException):
        await handler.to_response(Model(a=1, b="two"), RequestFactory().get("/", route_handler=handler))
