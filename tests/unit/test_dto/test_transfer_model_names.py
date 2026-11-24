from collections.abc import Iterator
from dataclasses import dataclass
from typing import Annotated, Any, Optional, get_args

import msgspec
import pytest

from litestar import Controller, Litestar, Router, WebSocket, get, post, websocket, websocket_listener
from litestar.dto import DataclassDTO, DTOConfig
from litestar.dto._backend import DTOBackend
from litestar.dto._plan import build_dto_plan, create_backend, handler_name_scope
from litestar.dto._registry import TransferModelNaming, TransferModelRegistry
from litestar.exceptions import LitestarWarning
from litestar.handlers import HTTPRouteHandler
from litestar.params import JSONBody
from litestar.routes import HTTPRoute, WebSocketRoute
from litestar.typing import FieldDefinition
from tests.unit.test_dto.schema_name_apps import APPS, describe

HANDLER_ID = "app.handlers.get_user::1"
SHORT = "GetUserUserResponseBody"
QUALIFIED = "app.handlers.get_userUserResponseBody"


@dataclass
class User:
    id: int
    name: str = "x"


@dataclass
class Post:
    author: User
    editor: User


@dataclass
class Item:
    name: str


@get("/", return_dto=DataclassDTO[Item], sync_to_thread=False)
def handler() -> Item:
    return Item(name="item")


@get("/posts", return_dto=DataclassDTO[Post], sync_to_thread=False)
def get_post() -> Post:
    return Post(author=User(id=1), editor=User(id=2))


@post("/posts", dto=DataclassDTO[Post], sync_to_thread=False)
def create_post(data: JSONBody[Post]) -> Post:
    return data


@get("/shared", return_dto=DataclassDTO[User], sync_to_thread=False)
def shared() -> User:
    return User(id=1)


@get("/a", return_dto=DataclassDTO[User], sync_to_thread=False)
def ha() -> User:
    return User(id=1)


@get("/b", return_dto=DataclassDTO[User], sync_to_thread=False)
def hb() -> User:
    return User(id=2)


class Base(Controller):
    @get(return_dto=DataclassDTO[User], sync_to_thread=False)
    def fetch(self) -> User:
        return User(id=1)


class A(Base):
    path = "/a"


class B(Base):
    path = "/b"


class RequiredArgumentBackend(DTOBackend):
    def __new__(cls, required: Any) -> "RequiredArgumentBackend":
        return super().__new__(cls)


class AnyArgumentsBackend(DTOBackend):
    def __new__(cls, *args: Any, **kwargs: Any) -> "AnyArgumentsBackend":
        return super().__new__(cls)


class SixKeywordBackend(DTOBackend):
    def __init__(
        self,
        dto_factory: Any,
        field_definition: FieldDefinition,
        handler_id: str,
        is_data_field: bool,
        model_type: type[Any],
        wrapper_attribute_name: str | None,
    ) -> None:
        super().__init__(
            dto_factory=dto_factory,
            field_definition=field_definition,
            handler_id=handler_id,
            is_data_field=is_data_field,
            model_type=model_type,
            wrapper_attribute_name=wrapper_attribute_name,
        )


class SkippingBackend(DTOBackend):
    def __init__(
        self,
        dto_factory: Any,
        field_definition: FieldDefinition,
        handler_id: str,
        is_data_field: bool,
        model_type: type[Any],
        wrapper_attribute_name: str | None,
    ) -> None:
        self.handler_id = handler_id  # pyright: ignore[reportAttributeAccessIssue,reportGeneralTypeIssues]
        self.is_data_field = is_data_field  # pyright: ignore[reportAttributeAccessIssue,reportGeneralTypeIssues]
        self.stored_name = self._create_transfer_model_name("User")


class NestingBackend(DTOBackend):
    def __init__(
        self,
        dto_factory: Any,
        field_definition: FieldDefinition,
        handler_id: str,
        is_data_field: bool,
        model_type: type[Any],
        wrapper_attribute_name: str | None,
    ) -> None:
        self.inner = DTOBackend(**six_keywords(handler_id=handler_id, is_data_field=is_data_field))
        super().__init__(
            dto_factory=dto_factory,
            field_definition=field_definition,
            handler_id=handler_id,
            is_data_field=is_data_field,
            model_type=model_type,
            wrapper_attribute_name=wrapper_attribute_name,
        )


def six_keywords(handler_id: str = HANDLER_ID, is_data_field: bool = False) -> dict[str, Any]:
    return {
        "dto_factory": DataclassDTO[User],
        "field_definition": FieldDefinition.from_annotation(User),
        "handler_id": handler_id,
        "is_data_field": is_data_field,
        "model_type": User,
        "wrapper_attribute_name": None,
    }


def build(backend_cls: type[DTOBackend], registry: TransferModelRegistry, name_scope: str) -> Any:
    return create_backend(
        DataclassDTO[User],
        FieldDefinition.from_annotation(User),
        is_data_field=False,
        handler_id=HANDLER_ID,
        backend_cls=backend_cls,
        naming=TransferModelNaming(registry, name_scope),
    )


def component_names(app: Litestar) -> list[str]:
    return sorted(app.openapi_schema.to_schema()["components"]["schemas"])


def _types(annotation: Any) -> Iterator[Any]:
    yield annotation
    for arg in get_args(annotation):
        yield from _types(arg)


def struct_names(struct: type[msgspec.Struct]) -> list[str]:
    names = [struct.__name__]
    for struct_field in msgspec.structs.fields(struct):
        for annotation in _types(struct_field.type):
            if isinstance(annotation, type) and issubclass(annotation, msgspec.Struct):
                names.extend(struct_names(annotation))
    return names


def plan_names(handler: HTTPRouteHandler, app: Litestar) -> list[str]:
    plan = build_dto_plan(handler, app)
    assert plan.return_ is not None
    return struct_names(plan.return_.backend.transfer_model_type)


def registered_handler(app: Litestar, path: str) -> HTTPRouteHandler:
    route = next(route for route in app.routes if isinstance(route, HTTPRoute) and route.path == path)
    return route.route_handler_map["GET"]


def test_component_names_are_stable_across_app_instances() -> None:
    first = Litestar([handler])
    second = Litestar([handler])

    assert component_names(first) == component_names(second) == ["HandlerItemResponseBody"]


def test_two_apps_from_same_handlers_produce_identical_documents() -> None:
    def build_app() -> Litestar:
        return Litestar(
            [
                get_post,
                create_post,
                A,
                B,
                Router("/r1", route_handlers=[shared]),
                Router("/r2", route_handlers=[shared]),
            ]
        )

    first = build_app()
    second = build_app()

    assert first.openapi_schema.to_schema() == second.openapi_schema.to_schema()


def test_names_do_not_depend_on_an_unrelated_app() -> None:
    def unrelated() -> HTTPRouteHandler:
        @get("/other", return_dto=DataclassDTO[Post], sync_to_thread=False)
        def get_post() -> Post:
            return Post(author=User(id=1), editor=User(id=2))

        return get_post

    Litestar([unrelated()])
    target = Litestar([get_post])

    assert component_names(target) == sorted(
        ["GetPostPostResponseBody", "GetPostPostUserResponseBody", "GetPostPost_editorUserResponseBody"]
    )


@dataclass
class Holder:
    maybe: Optional[User]
    many: list[User]
    first: User
    second: User


def test_nested_models_of_one_type_under_several_fields_get_unqualified_names() -> None:
    @get("/holders", return_dto=DataclassDTO[Holder], sync_to_thread=False)
    def get_holder() -> Holder:
        return Holder(maybe=None, many=[], first=User(id=1), second=User(id=2))

    app = Litestar([get_holder])

    assert component_names(app) == [
        "GetHolderHolderResponseBody",
        "GetHolderHolderUserResponseBody",
        "GetHolderHolder_0UserResponseBody",
        "GetHolderHolder_0_manyUserResponseBody",
        "GetHolderHolder_secondUserResponseBody",
    ]


def test_register_keeps_existing_component_names() -> None:
    app = Litestar([ha])
    before = component_names(app)

    with pytest.warns(LitestarWarning):
        app.register(hb)
    after = component_names(app)

    assert set(before) <= set(after)
    assert "HbUserResponseBody" in after


def test_rebuilding_a_plan_returns_the_same_names() -> None:
    app = Litestar([Router("/r", route_handlers=[get_post])])
    registered = registered_handler(app, "/r/posts")
    assert registered._dto_plan is not None
    assert registered._dto_plan.return_ is not None
    original = struct_names(registered._dto_plan.return_.backend.transfer_model_type)

    assert plan_names(registered, app) == original
    assert plan_names(registered.merge(), app) == original
    assert original == ["GetPostPostResponseBody", "GetPostPostUserResponseBody", "GetPostPost_editorUserResponseBody"]


def test_rebuilding_a_plan_reserves_no_new_name() -> None:
    app = Litestar([Router("/r", route_handlers=[get_post])])
    registered = registered_handler(app, "/r/posts")
    plan_names(registered, app)
    plan_names(registered.merge(), app)

    with pytest.warns(LitestarWarning):
        app.register(Router("/second", route_handlers=[get_post]))

    second = registered_handler(app, "/second/posts")
    assert second._dto_plan is not None
    assert second._dto_plan.return_ is not None
    assert second._dto_plan.return_.backend.transfer_model_type.__name__ == f"{get_post!s}PostResponseBody"


def test_backend_subclass_with_six_keyword_constructor() -> None:
    registry = TransferModelRegistry()

    names = [build(SixKeywordBackend, registry, scope).transfer_model_type.__name__ for scope in ("s1", "s2")]

    assert names == [SHORT, QUALIFIED]


def test_backend_subclass_that_skips_the_base_constructor() -> None:
    registry = TransferModelRegistry()

    names = [build(SkippingBackend, registry, scope).stored_name for scope in ("s1", "s2")]

    assert names == [SHORT, QUALIFIED]


def test_names_requested_after_construction_use_the_registry() -> None:
    registry = TransferModelRegistry()
    skipping = build(SkippingBackend, registry, "s1")
    stock = build(DTOBackend, registry, "s2")

    assert stock._create_transfer_model_name("Late") == "GetUserLateResponseBody"
    assert skipping._create_transfer_model_name("Late") == "app.handlers.get_userLateResponseBody"


def test_backend_constructed_inside_a_constructor_is_private() -> None:
    registry = TransferModelRegistry()
    build(DTOBackend, registry, "s0")

    nesting = build(NestingBackend, registry, "s1")

    assert nesting.transfer_model_type.__name__ == QUALIFIED
    assert nesting.inner.transfer_model_type.__name__ == SHORT


def test_standalone_backends_do_not_share_names() -> None:
    field_definition = FieldDefinition.from_annotation(User)
    created = [
        create_backend(DataclassDTO[User], field_definition, is_data_field=True, handler_id="test") for _ in "ab"
    ]
    direct = [DTOBackend(**six_keywords(handler_id="test", is_data_field=True)) for _ in "ab"]

    assert [backend.transfer_model_type.__name__ for backend in (*created, *direct)] == ["TestUserRequestBody"] * 4


def test_websocket_listeners_on_one_path_share_transfer_model_names() -> None:
    def listener(exclude: set[str]) -> Any:
        @websocket_listener("/ws", dto=DataclassDTO[Annotated[User, DTOConfig(exclude=exclude)]])
        async def handler(data: User) -> None:
            return None

        return handler

    app = Litestar([listener({"id"}), listener({"name"})])
    structs = []
    for route in app.routes:
        if isinstance(route, WebSocketRoute):
            plan = route.route_handler._dto_plan
            assert plan is not None
            assert plan.data is not None
            structs.append(plan.data.backend.transfer_model_type)

    assert len(structs) == 2
    assert structs[0].__name__ == structs[1].__name__
    assert [{struct_field.name for struct_field in msgspec.structs.fields(struct)} for struct in structs] in (
        [{"name"}, {"id"}],
        [{"id"}, {"name"}],
    )


def test_backend_subclass_whose_new_requires_arguments_raises() -> None:
    with pytest.raises(TypeError):
        create_backend(
            DataclassDTO[User],
            FieldDefinition.from_annotation(User),
            is_data_field=False,
            handler_id=HANDLER_ID,
            backend_cls=RequiredArgumentBackend,
        )


def test_backend_subclass_whose_new_accepts_any_arguments() -> None:
    backend = build(AnyArgumentsBackend, TransferModelRegistry(), "s1")

    assert type(backend) is AnyArgumentsBackend
    assert backend.transfer_model_type.__name__ == SHORT


EXPECTED: dict[str, dict[str, Any]] = {
    "single": {
        "components": [
            "CreateUserUserRequestBody",
            "CreateUserUserResponseBody",
            "GetUserUserResponseBody",
            "ListUsersUserResponseBody",
            "PatchUserUserRequestBody",
        ],
        "operations": {
            "GET /users": ["GetUserUserResponseBody"],
            "POST /users": ["CreateUserUserRequestBody", "CreateUserUserResponseBody"],
            "POST /users/partial": ["PatchUserUserRequestBody"],
            "GET /users/all": ["ListUsersUserResponseBody"],
        },
    },
    "nested": {
        "components": [
            "CreatePostPostRequestBody",
            "CreatePostPostResponseBody",
            "CreatePostPostUserRequestBody",
            "CreatePostPostUserResponseBody",
            "CreatePostPost_0TagRequestBody",
            "CreatePostPost_0TagResponseBody",
            "CreatePostPost_editorUserRequestBody",
            "CreatePostPost_editorUserResponseBody",
            "GetPostPostResponseBody",
            "GetPostPostUserResponseBody",
            "GetPostPost_0TagResponseBody",
            "GetPostPost_editorUserResponseBody",
        ],
        "operations": {
            "GET /posts": ["GetPostPostResponseBody"],
            "POST /posts": ["CreatePostPostRequestBody", "CreatePostPostResponseBody"],
        },
    },
    "same_handler_name": {
        "components": [
            "FetchUserResponseBody",
            "tests.unit.test_dto.schema_name_apps.same_handler_name.SecondController.fetchUserResponseBody",
        ],
        "operations": {
            "GET /first": ["FetchUserResponseBody"],
            "GET /second": [
                "tests.unit.test_dto.schema_name_apps.same_handler_name.SecondController.fetchUserResponseBody"
            ],
        },
    },
    "schema_name": {
        "components": [
            "GetPostPostUserResponseBody",
            "GetPostPost_0TagResponseBody",
            "GetPostPost_editorUserResponseBody",
            "PublicPost",
        ],
        "operations": {"GET /posts": ["PublicPost"], "GET /posts/all": ["PublicPost"]},
    },
    "generic_wrapper": {
        "components": ["Envelope_litestar.dto._backend.GetWrappedUserResponseBody_", "GetWrappedUserResponseBody"],
        "operations": {"GET /users": ["Envelope_litestar.dto._backend.GetWrappedUserResponseBody_"]},
    },
    "msgspec_nested": {
        "components": ["GetProductProductMakerResponseBody", "GetProductProductResponseBody"],
        "operations": {"GET /products": ["GetProductProductResponseBody"]},
    },
    "pydantic_nested": {
        "components": ["GetPetPetOwnerResponseBody", "GetPetPetResponseBody"],
        "operations": {"GET /pets": ["GetPetPetResponseBody"]},
    },
}


@pytest.mark.parametrize("app_id", sorted(EXPECTED))
def test_component_names_of_example_apps(app_id: str) -> None:
    if app_id.startswith("pydantic"):
        pytest.importorskip("pydantic")

    assert [describe(APPS[app_id]()) for _ in range(3)] == [EXPECTED[app_id]] * 3


def plain_fetch() -> None:
    return None


@get("/x")
async def scoped_handler() -> None:
    return None


def test_name_for_returns_preferred_when_free() -> None:
    assert TransferModelRegistry().name_for("k", "A", "m.A") == "A"


def test_name_for_falls_back_to_qualified_then_numbered() -> None:
    registry = TransferModelRegistry()

    assert [registry.name_for(key, "A", "m.A") for key in ("k1", "k2", "k3", "k4")] == ["A", "m.A", "m.A_0", "m.A_1"]


def test_name_for_is_idempotent_per_key() -> None:
    registry = TransferModelRegistry()

    first = registry.name_for("k", "A", "m.A")
    repeated = registry.name_for("k", "B", "m.B")

    assert (first, repeated) == ("A", "A")
    assert registry.name_for("other", "A", "m.A") == "m.A"


def test_registries_are_independent() -> None:
    assert TransferModelRegistry().name_for("k", "A", "m.A") == TransferModelRegistry().name_for("k", "A", "m.A") == "A"


def test_naming_numbers_repeats_of_one_model_name() -> None:
    naming = TransferModelNaming(TransferModelRegistry(), "scope")

    names = [naming.name_for(is_data_field=False, model_name="PostUser", preferred="A", qualified="m.A") for _ in "abc"]

    assert names == ["A", "m.A", "m.A_0"]


def test_naming_with_same_scope_reuses_names() -> None:
    registry = TransferModelRegistry()

    def three_names(naming: TransferModelNaming) -> list[str]:
        return [
            naming.name_for(is_data_field=False, model_name="PostUser", preferred="A", qualified="m.A") for _ in "abc"
        ]

    first = three_names(TransferModelNaming(registry, "scope"))
    second = three_names(TransferModelNaming(registry, "scope"))
    other = TransferModelNaming(registry, "other").name_for(
        is_data_field=False, model_name="PostUser", preferred="A", qualified="m.A"
    )

    assert first == second == ["A", "m.A", "m.A_0"]
    assert other == "m.A_1"


def test_naming_counts_ordinals_across_directions() -> None:
    registry = TransferModelRegistry()

    def both_directions(naming: TransferModelNaming) -> list[str]:
        return [
            naming.name_for(is_data_field=True, model_name="PostUser", preferred="Req", qualified="m.Req"),
            naming.name_for(is_data_field=False, model_name="PostUser", preferred="Resp", qualified="m.Resp"),
        ]

    assert both_directions(TransferModelNaming(registry, "scope")) == ["Req", "Resp"]
    assert both_directions(TransferModelNaming(registry, "scope")) == ["Req", "Resp"]


def test_handler_name_scope_survives_merge() -> None:
    router = Router("/r", route_handlers=[scoped_handler])

    first = scoped_handler.merge(router)
    second = scoped_handler.merge(router)

    assert first is not second
    assert handler_name_scope(first) == handler_name_scope(second)


def test_handler_name_scope_separates_one_handler_under_two_routers() -> None:
    first = scoped_handler.merge(Router("/r1", route_handlers=[scoped_handler]))
    second = scoped_handler.merge(Router("/r2", route_handlers=[scoped_handler]))

    assert handler_name_scope(first) != handler_name_scope(second)


def test_handler_name_scope_separates_http_methods() -> None:
    assert handler_name_scope(get("/s")(plain_fetch)) != handler_name_scope(post("/s")(plain_fetch))


def test_handler_name_scope_for_websocket_handler() -> None:
    @websocket("/ws")
    async def socket_handler(socket: WebSocket) -> None:
        return None

    scope = handler_name_scope(socket_handler)

    assert isinstance(scope, tuple)
    assert hash(scope) == hash(handler_name_scope(socket_handler))
    assert scope[3] == ()
