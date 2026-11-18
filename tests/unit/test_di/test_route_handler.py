import inspect
import warnings
from collections.abc import AsyncGenerator, Generator
from functools import partial
from typing import Any, Optional

import pytest

from litestar import Controller, Litestar, Request, Router, WebSocket, get, post, websocket, websocket_listener
from litestar.config.app import AppConfig
from litestar.connection import ASGIConnection
from litestar.datastructures import Headers, ImmutableState, State
from litestar.di import (
    InjectionParameter,
    NamedDependency,
    Provide,
    Provider,
    ProviderKind,
    TypeDependency,
)
from litestar.di.exceptions import DIRegistrationError, MissingProviderError
from litestar.exceptions import ImproperlyConfiguredException, LitestarWarning
from litestar.params import FromPath, FromQuery, JSONBody, QueryParameter, QueryParams, RawBody, RequestCookies
from litestar.plugins import DIPlugin, InitPlugin
from litestar.testing import create_test_client
from litestar.types import Scope


def test_provide_becomes_provider_with_scope_handler() -> None:
    async def provide_value() -> int:
        return 1

    @get("/")
    async def handler(value: NamedDependency[int]) -> None: ...

    app = Litestar([handler], dependencies={"value": Provide(provide_value)}, openapi_config=None)
    provider = app.route_handler_method_map["/"]["GET"]._injection_setup.registry.providers["value"]

    assert provider.scope == "handler"
    assert provider.kind is ProviderKind.NAMED
    assert provider.fn is provide_value


def test_cached_provide_becomes_provider_with_scope_app() -> None:
    async def provide_value() -> int:
        return 1

    @get("/")
    async def handler(value: NamedDependency[int]) -> None: ...

    app = Litestar([handler], dependencies={"value": Provide(provide_value, use_cache=True)}, openapi_config=None)

    assert app.route_handler_method_map["/"]["GET"]._injection_setup.registry.providers["value"].scope == "app"


def test_sync_provide_without_sync_to_thread_raises() -> None:
    def provide_value() -> int:
        return 1

    @get("/")
    async def handler(value: NamedDependency[int]) -> None: ...

    with pytest.raises(
        DIRegistrationError,
        match=r"^\[paths='/', handler='handler', dependencies='value'\] Missing 'sync_to_thread' on synchronous "
        r"callable .*provide_value .*\. A synchronous callable must declare whether it needs to run in a separate "
        r"thread: An undeclared blocking call would otherwise block the event loop\.$",
    ):
        Litestar([handler], dependencies={"value": Provide(provide_value)}, openapi_config=None)


def test_sync_provide_with_sync_to_thread_keeps_sync_to_thread() -> None:
    def provide_value() -> int:
        return 1

    @get("/")
    async def handler(value: NamedDependency[int]) -> None: ...

    app = Litestar([handler], dependencies={"value": Provide(provide_value, sync_to_thread=True)}, openapi_config=None)
    provider = app.route_handler_method_map["/"]["GET"]._injection_setup.registry.providers["value"]

    assert provider.sync_to_thread is True
    assert provider.fn is provide_value


def test_class_provide_has_sync_to_thread_false() -> None:
    class Value:
        pass

    @get("/")
    async def handler(value: NamedDependency[Value]) -> None: ...

    app = Litestar([handler], dependencies={"value": Provide(Value)}, openapi_config=None)
    provider = app.route_handler_method_map["/"]["GET"]._injection_setup.registry.providers["value"]

    assert provider.sync_to_thread is False
    assert provider.fn is Value


@pytest.mark.usefixtures("enable_warn_implicit_sync_to_thread")
def test_bare_sync_callable_warns_and_has_sync_to_thread_false() -> None:
    def provide_value() -> int:
        return 1

    @get("/")
    async def handler(value: NamedDependency[int]) -> None: ...

    with pytest.warns(LitestarWarning, match="without setting sync_to_thread"):
        app = Litestar([handler], dependencies={"value": provide_value}, openapi_config=None)
    provider = app.route_handler_method_map["/"]["GET"]._injection_setup.registry.providers["value"]

    assert provider.sync_to_thread is False
    assert provider.fn is provide_value


@pytest.mark.usefixtures("enable_warn_implicit_sync_to_thread")
def test_bare_class_callable_has_sync_to_thread_false_without_warning() -> None:
    class Value:
        pass

    @get("/")
    async def handler(value: NamedDependency[Value]) -> None: ...

    with warnings.catch_warnings():
        warnings.simplefilter("error", LitestarWarning)
        app = Litestar([handler], dependencies={"value": Value}, openapi_config=None)

    assert app.route_handler_method_map["/"]["GET"]._injection_setup.registry.providers["value"].sync_to_thread is False


def test_async_provide_with_sync_to_thread_raises() -> None:
    async def provide_value() -> int:
        return 1

    @get("/")
    async def handler(value: NamedDependency[int]) -> None: ...

    with pytest.raises(
        DIRegistrationError,
        match=r"^\[paths='/', handler='handler', dependencies='value'\] sync_to_thread=True has no effect on "
        r".*provide_value .* because it is not a synchronous callable$",
    ):
        Litestar([handler], dependencies={"value": Provide(provide_value, sync_to_thread=True)}, openapi_config=None)


def test_async_generator_provide() -> None:
    async def provide_value() -> AsyncGenerator[int, None]:
        yield 1

    @get("/")
    async def handler(value: NamedDependency[int]) -> None: ...

    app = Litestar([handler], dependencies={"value": Provide(provide_value)}, openapi_config=None)

    assert app.route_handler_method_map["/"]["GET"]._injection_setup.registry.providers["value"].fn is provide_value


def test_cached_generator_provide_becomes_app_scoped_provider() -> None:
    async def provide_value() -> AsyncGenerator[int, None]:
        yield 1

    @get("/")
    async def handler(value: NamedDependency[int]) -> None: ...

    app = Litestar([handler], dependencies={"value": Provide(provide_value, use_cache=True)}, openapi_config=None)

    assert app.route_handler_method_map["/"]["GET"]._injection_setup.registry.providers["value"].scope == "app"


def test_provider_declaration_is_used_as_is() -> None:
    async def provide_value() -> int:
        return 1

    @get("/")
    async def handler(value: NamedDependency[int]) -> None: ...

    provider = Provider(provide_value, key="value")
    app = Litestar([handler], dependencies={"value": provider}, openapi_config=None)

    assert app.route_handler_method_map["/"]["GET"]._injection_setup.registry.providers["value"] is provider


@pytest.mark.parametrize("declare", [Provide, lambda cls: Provider(cls, key="value")], ids=["Provide", "Provider"])
def test_class_dependency_reads_signature_from_di_plugin(declare: Any) -> None:
    class Value:
        def __init__(self, **kwargs: Any) -> None:
            pass

    class Plugin(DIPlugin):
        def has_typed_init(self, type_: Any) -> bool:
            return type_ is Value

        def get_typed_init(self, type_: Any) -> tuple[inspect.Signature, dict[str, Any]]:
            parameter = inspect.Parameter("number", inspect.Parameter.KEYWORD_ONLY)
            return inspect.Signature([parameter]), {"number": NamedDependency[int]}

    async def provide_number() -> int:
        return 1

    @get("/")
    async def handler(value: NamedDependency[Value]) -> None: ...

    app = Litestar(
        [handler],
        dependencies={"value": declare(Value), "number": Provide(provide_number)},
        plugins=[Plugin()],
        openapi_config=None,
    )

    assert app.route_handler_method_map["/"]["GET"]._injection_setup.registry.providers["value"].dependencies == (
        InjectionParameter(parameter_name="number", key="number", kind=ProviderKind.NAMED),
    )


def test_class_dependency_registered_again_after_di_plugin_signature_failed_raises() -> None:
    class Value:
        pass

    class Plugin(DIPlugin):
        def has_typed_init(self, type_: Any) -> bool:
            return type_ is Value

        def get_typed_init(self, type_: Any) -> tuple[inspect.Signature, dict[str, Any]]:
            return inspect.Signature([inspect.Parameter("number", inspect.Parameter.KEYWORD_ONLY)]), {"number": int}

    declaration = Provide(Value)

    @get("/one", dependencies={"value": declaration})
    async def one(value: NamedDependency[Value]) -> None: ...

    @get("/two", dependencies={"value": declaration})
    async def two(value: NamedDependency[Value]) -> None: ...

    app = Litestar([], plugins=[Plugin()], openapi_config=None)

    for handler in (one, two):
        with pytest.raises(
            DIRegistrationError, match="Parameter 'number' of provider .* is not marked as a dependency"
        ):
            app.register(handler)


def test_dependency_registry_of_http_handler() -> None:
    async def provide_value(page: FromQuery[int]) -> int:
        return page

    @post("/", dependencies={"value": Provide(provide_value)})
    async def handler(value: NamedDependency[int], token: FromQuery[str]) -> None: ...

    app = Litestar([handler], openapi_config=None)
    registry = app.route_handler_method_map["/"]["POST"]._injection_setup.registry

    assert registry.is_frozen
    assert set(registry.providers) == {
        Litestar,
        Request,
        ASGIConnection,
        Headers,
        QueryParams,
        RequestCookies,
        Scope,
        RawBody,
        "query:page",
        "query:token",
        "value",
    }


def test_dependency_registry_of_get_handler_has_no_body() -> None:
    @get("/")
    async def handler() -> None: ...

    app = Litestar([handler], openapi_config=None)

    assert RawBody not in app.route_handler_method_map["/"]["GET"]._injection_setup.registry.providers


def test_get_handler_raw_body_raises() -> None:
    @get("/")
    async def handler(body: RawBody) -> None: ...

    with pytest.raises(ImproperlyConfiguredException) as exc_info:
        Litestar([handler], openapi_config=None)
    assert exc_info.value.detail == (
        "[paths='/', handler='handler'] Parameter 'body' of handler 'handler' declares the raw request body, which a "
        "handler whose methods include 'GET' does not take"
    )


def test_get_handler_raw_body_with_default_raises() -> None:
    @get("/")
    async def handler(body: RawBody = RawBody(b"default")) -> None: ...

    with pytest.raises(ImproperlyConfiguredException) as exc_info:
        Litestar([handler], openapi_config=None)
    assert exc_info.value.detail == (
        "[paths='/', handler='handler'] Parameter 'body' of handler 'handler' declares the raw request body, which a "
        "handler whose methods include 'GET' does not take"
    )


def test_get_handler_provider_raw_body_with_default_raises() -> None:
    async def provide_value(body: RawBody = RawBody(b"default")) -> bytes:
        return body

    @get("/", dependencies={"value": Provide(provide_value)})
    async def handler(value: NamedDependency[bytes]) -> None: ...

    with pytest.raises(ImproperlyConfiguredException) as exc_info:
        Litestar([handler], openapi_config=None)
    assert exc_info.value.detail == (
        "[paths='/', handler='handler'] Parameter 'body' of provider 'value' declares the raw request body, which a "
        "handler whose methods include 'GET' does not take"
    )


def test_get_handler_provider_data_raises() -> None:
    async def provide_value(data: JSONBody[dict[str, int]]) -> dict[str, int]:
        return data

    @get("/", dependencies={"value": Provide(provide_value)})
    async def handler(value: NamedDependency[dict[str, int]]) -> None: ...

    with pytest.raises(ImproperlyConfiguredException) as exc_info:
        Litestar([handler], openapi_config=None)
    assert exc_info.value.detail == (
        "[paths='/', handler='handler'] Parameter 'data' of provider 'value' declares the request body, which a "
        "handler whose methods include 'GET' does not take"
    )


def test_websocket_handler_provider_raw_body_raises() -> None:
    async def provide_value(body: RawBody) -> bytes:
        return body

    @websocket("/", dependencies={"value": Provide(provide_value)})
    async def handler(socket: WebSocket, value: NamedDependency[bytes]) -> None: ...

    with pytest.raises(ImproperlyConfiguredException) as exc_info:
        Litestar([handler], openapi_config=None)
    assert exc_info.value.detail == (
        "[paths='/', handler='handler'] Parameter 'body' of provider 'value' declares the raw request body, which a "
        "websocket handler does not take"
    )


def test_unused_provider_request_in_websocket_handler() -> None:
    async def provide_path(request: Request) -> str:
        return request.url.path

    @get("/http")
    async def http_handler(path: NamedDependency[str]) -> str:
        return path

    @websocket("/ws")
    async def websocket_handler(socket: WebSocket) -> None:
        await socket.accept()
        await socket.send_text("hello")
        await socket.close()

    with create_test_client(
        [http_handler, websocket_handler], dependencies={"path": Provide(provide_path)}, openapi_config=None
    ) as client:
        assert client.get("/http").text == "/http"
        with client.websocket_connect("/ws") as socket:
            assert socket.receive_text() == "hello"


def test_unused_provider_path_parameter_not_in_path() -> None:
    async def provide_user(user_id: FromPath[int]) -> str:
        return f"user {user_id}"

    @get("/{user_id:int}")
    async def one(user: NamedDependency[str]) -> str:
        return user

    @get("/")
    async def many() -> str:
        return "all users"

    router = Router("/users", route_handlers=[one, many], dependencies={"user": Provide(provide_user)})
    with create_test_client([router], openapi_config=None) as client:
        assert client.get("/users/3").text == "user 3"
        assert client.get("/users").text == "all users"


def test_unused_provider_data_in_get_handler() -> None:
    async def provide_name(data: JSONBody[dict[str, str]]) -> str:
        return data["name"]

    @post("/people")
    async def create(name: NamedDependency[str]) -> str:
        return name

    @get("/health")
    async def health() -> str:
        return "ok"

    with create_test_client(
        [create, health], dependencies={"name": Provide(provide_name)}, openapi_config=None
    ) as client:
        assert client.post("/people", json={"name": "a"}).text == "a"
        assert client.get("/health").text == "ok"


@pytest.mark.parametrize("first", ["detail", "health"])
def test_unused_provider_depending_on_lower_layer(first: str) -> None:
    async def provide_repository() -> str:
        return "repository"

    async def provide_service(repository: NamedDependency[str]) -> str:
        return repository + " service"

    @get("/detail", dependencies={"repository": Provide(provide_repository)})
    async def detail(service: NamedDependency[str]) -> str:
        return service

    @get("/health")
    async def health() -> str:
        return "ok"

    handlers = [detail, health] if first == "detail" else [health, detail]
    with create_test_client(
        handlers, dependencies={"service": Provide(provide_service)}, openapi_config=None
    ) as client:
        assert client.get("/detail").text == "repository service"
        assert client.get("/health").text == "ok"


@pytest.mark.parametrize("scope", ["app", "request"])
def test_unused_provider_of_outer_scope_is_registered(scope: str) -> None:
    async def provide_value() -> int:
        return 1

    async def provide_other() -> int:
        return 2

    @get("/")
    async def handler() -> None: ...

    app = Litestar(
        [handler],
        dependencies=[Provider(provide_value, key="value", scope=scope), Provider(provide_other, key="other")],
        openapi_config=None,
    )
    providers = app.route_handler_method_map["/"]["GET"]._injection_setup.registry.providers

    assert "value" in providers
    assert "other" not in providers


@pytest.mark.parametrize("scope", ["app", "request"])
def test_unused_provider_of_outer_scope_depending_on_lower_layer_raises(scope: str) -> None:
    async def provide_repository() -> str:
        return "repository"

    async def provide_service(repository: NamedDependency[str]) -> str:
        return repository + " service"

    @get("/detail", dependencies=[Provider(provide_repository, key="repository", scope=scope)])
    async def detail(service: NamedDependency[str]) -> str:
        return service

    @get("/health")
    async def health() -> str:
        return "ok"

    router = Router(
        "/things",
        route_handlers=[detail, health],
        dependencies=[Provider(provide_service, key="service", scope=scope)],
    )
    with pytest.raises(MissingProviderError) as exc_info:
        Litestar([router], openapi_config=None)

    assert str(exc_info.value).startswith(
        "Registry \"[paths='/things/health', handler='health']\" has no provider for dependency 'repository'."
    )
    assert exc_info.value.__notes__ == [
        "Handler 'health' does not use 'service'. Its registry holds the providers of scope 'app' and 'request' of "
        "its layers and what they depend on"
    ]


def test_app_provider_of_outer_scope_depending_on_lower_layer_raises() -> None:
    async def provide_repository() -> str:
        return "repository"

    async def provide_service(repository: NamedDependency[str]) -> str:
        return repository + " service"

    @get("/", dependencies=[Provider(provide_repository, key="repository", scope="app")])
    async def handler(service: NamedDependency[str]) -> str:
        return service

    with pytest.raises(MissingProviderError) as exc_info:
        Litestar([handler], dependencies=[Provider(provide_service, key="service", scope="app")], openapi_config=None)

    assert str(exc_info.value).startswith(
        "Registry \"[paths='/', handler='options_handler']\" has no provider for dependency 'repository'."
    )


def test_missing_provider_error_of_used_provider_has_no_note() -> None:
    async def provide_service(repository: NamedDependency[str]) -> str:
        return repository + " service"

    @get("/", dependencies={"service": Provide(provide_service)})
    async def handler(service: NamedDependency[str]) -> str:
        return service

    with pytest.raises(MissingProviderError, match="has no provider for dependency 'repository'") as exc_info:
        Litestar([handler], openapi_config=None)

    assert not hasattr(exc_info.value, "__notes__")


def test_dependency_registry_of_websocket_handler() -> None:
    @websocket("/")
    async def handler(socket: WebSocket) -> None: ...

    app = Litestar([handler], openapi_config=None)
    registry = app.route_handler_method_map["/"]["websocket"]._injection_setup.registry

    assert set(registry.providers) == {Litestar, WebSocket, ASGIConnection, Headers, QueryParams, RequestCookies, Scope}


def test_dependency_registry_seeds_connection_class_chain() -> None:
    class CustomRequest(Request):
        pass

    @get("/")
    async def handler() -> None: ...

    app = Litestar([handler], request_class=CustomRequest, openapi_config=None)
    providers = app.route_handler_method_map["/"]["GET"]._injection_setup.registry.providers

    assert {CustomRequest, Request, ASGIConnection} <= set(providers)
    assert all(providers[key].is_seed for key in (CustomRequest, Request, ASGIConnection))


def test_dependency_registries_share_one_seed_per_connection_class() -> None:
    @get("/a")
    async def first() -> None: ...

    @get("/b")
    async def second() -> None: ...

    @websocket("/ws")
    async def socket_handler(socket: WebSocket) -> None: ...

    app = Litestar([first, second, socket_handler], openapi_config=None)
    first_providers = app.route_handler_method_map["/a"]["GET"]._injection_setup.registry.providers
    second_providers = app.route_handler_method_map["/b"]["GET"]._injection_setup.registry.providers
    socket_providers = app.route_handler_method_map["/ws"]["websocket"]._injection_setup.registry.providers

    assert first_providers[Request] is second_providers[Request]
    assert first_providers[ASGIConnection] is second_providers[ASGIConnection] is socket_providers[ASGIConnection]


def test_dependency_registry_connection_seeds_and_request_values_have_scope_handler() -> None:
    @post("/{item_id:int}")
    async def handler(item_id: FromPath[int], data: JSONBody[dict]) -> None: ...

    app = Litestar([handler], openapi_config=None)
    providers = app.route_handler_method_map["/{item_id:int}"]["POST"]._injection_setup.registry.providers
    keys = {
        Request,
        ASGIConnection,
        Headers,
        QueryParams,
        RequestCookies,
        Scope,
        RawBody,
        "path:item_id",
    }

    assert {key: provider.scope for key, provider in providers.items() if key in keys} == dict.fromkeys(keys, "handler")


def test_dependency_registry_seeds_app_subclass() -> None:
    class App(Litestar):
        pass

    @get("/")
    async def handler() -> None: ...

    app = App([handler], openapi_config=None)
    providers = app.route_handler_method_map["/"]["GET"]._injection_setup.registry.providers

    assert providers[Litestar].is_seed
    assert providers[App].is_seed


def test_dependency_registry_provides_declared_state_classes() -> None:
    class CustomState(State):
        pass

    class CustomImmutableState(ImmutableState):
        pass

    async def provide_value(state: CustomState, immutable_state: CustomImmutableState) -> int:
        return 1

    @get("/", dependencies={"value": Provide(provide_value)})
    async def handler(state: State, immutable_state: ImmutableState, value: NamedDependency[int]) -> None: ...

    app = Litestar([handler], openapi_config=None)
    providers = app.route_handler_method_map["/"]["GET"]._injection_setup.registry.providers

    assert providers[State].scope == "app"
    assert providers[CustomState].scope == "app"
    assert providers[ImmutableState].scope == "request"
    assert providers[CustomImmutableState].scope == "request"


def test_dependency_registry_one_provider_per_declaration() -> None:
    async def provide_value() -> int:
        return 1

    @get("/one")
    async def one(value: NamedDependency[int]) -> None: ...

    @get("/two")
    async def two(value: NamedDependency[int]) -> None: ...

    app = Litestar([one, two], dependencies={"value": Provide(provide_value)}, openapi_config=None)

    assert (
        app.route_handler_method_map["/one"]["GET"]._injection_setup.registry.providers["value"]
        is app.route_handler_method_map["/two"]["GET"]._injection_setup.registry.providers["value"]
    )


def test_one_provide_under_two_keys_gives_two_providers() -> None:
    async def provide_value() -> int:
        return 1

    @get("/")
    async def handler(a: NamedDependency[int], b: NamedDependency[int]) -> list[int]:
        return [a, b]

    declaration = Provide(provide_value)

    with create_test_client([handler], dependencies={"a": declaration, "b": declaration}) as client:
        providers = client.app.route_handler_method_map["/"]["GET"]._injection_setup.registry.providers

        assert providers["a"] is not providers["b"]
        assert client.get("/").json() == [1, 1]


def test_request_parameters_of_function_and_provider_are_seeds() -> None:
    async def provide_value(page: FromQuery[int]) -> int:
        return page

    @get("/", dependencies={"value": Provide(provide_value)})
    async def handler(value: NamedDependency[int], token: FromQuery[str]) -> None: ...

    app = Litestar([handler], openapi_config=None)
    providers = app.route_handler_method_map["/"]["GET"]._injection_setup.registry.providers

    assert providers["query:page"].is_seed
    assert providers["query:token"].is_seed


def test_layer_parameter_nothing_declares_is_seed() -> None:
    @get("/")
    async def handler() -> None: ...

    app = Litestar(
        [handler], parameters={"limit": QueryParameter(annotation=int, name="page-limit")}, openapi_config=None
    )
    setup = app.route_handler_method_map["/"]["GET"]._injection_setup

    assert "query:page-limit" in setup.request_parameter_definitions
    assert setup.registry.providers["query:page-limit"].is_seed


def test_fn_injection_target_binds_layer_parameter_through_bare_marker() -> None:
    @get("/")
    async def handler(limit: FromQuery[int]) -> None: ...

    app = Litestar(
        [handler], parameters={"limit": QueryParameter(annotation=int, name="page-limit")}, openapi_config=None
    )

    assert app.route_handler_method_map["/"]["GET"]._injection_setup.target.dependencies == (
        InjectionParameter(parameter_name="limit", key="query:page-limit", kind=ProviderKind.NAMED),
    )


def test_unmarked_parameter_named_like_layer_parameter_raises() -> None:
    @get("/")
    async def handler(limit: int) -> None: ...

    with pytest.raises(ImproperlyConfiguredException) as exc_info:
        Litestar([handler], parameters={"limit": QueryParameter(annotation=int)}, openapi_config=None)
    assert exc_info.value.detail == "[paths='/', handler='handler'] Missing declaration for parameter 'limit'"


@pytest.mark.parametrize(("args", "kwargs"), [((1,), {}), ((), {"x": 1})], ids=["positional", "keyword"])
def test_fn_injection_target_of_partial_omits_bound_marked_parameter(
    args: tuple[Any, ...], kwargs: dict[str, Any]
) -> None:
    async def handler(x: FromQuery[int], page: FromQuery[int]) -> None: ...

    app = Litestar([get("/")(partial(handler, *args, **kwargs))], openapi_config=None)

    assert app.route_handler_method_map["/"]["GET"]._injection_setup.target.dependencies == (
        InjectionParameter(parameter_name="page", key="query:page", kind=ProviderKind.NAMED),
    )


def test_unmarked_parameter_bound_by_partial_raises() -> None:
    async def handler(x: int, page: FromQuery[int]) -> None: ...

    with pytest.raises(ImproperlyConfiguredException) as exc_info:
        Litestar([get("/")(partial(handler, x=1))], openapi_config=None)
    assert exc_info.value.detail == "[paths='/', handler='handler'] Missing declaration for parameter 'x'"


def test_marked_var_positional_parameter_raises() -> None:
    @get("/")
    async def handler(*args: FromQuery[Any]) -> None: ...

    with pytest.raises(
        DIRegistrationError,
        match=r"^\[paths='/', handler='handler'\] Parameter '\*args' of .* is marked as a dependency but is variadic",
    ):
        Litestar([handler], openapi_config=None)


def test_marked_var_keyword_parameter_raises() -> None:
    @get("/")
    async def handler(**kwargs: FromQuery[Any]) -> None: ...

    with pytest.raises(
        DIRegistrationError,
        match=r"^\[paths='/', handler='handler'\] Parameter '\*\*kwargs' of .* is marked as a dependency but is variadic",
    ):
        Litestar([handler], openapi_config=None)


def test_handler_dependency_typed_optional_without_provider_raises() -> None:
    @get("/")
    async def handler(value: NamedDependency[Optional[int]]) -> None: ...

    with pytest.raises(MissingProviderError, match="has no provider for dependency 'value'"):
        Litestar([handler], openapi_config=None)


def test_provider_signature_error_names_handler_and_key() -> None:
    async def provide_value(headers: dict[str, str]) -> str:
        return "x"

    @get("/", dependencies={"value": provide_value})
    async def one(value: NamedDependency[str]) -> str:
        return value

    with pytest.raises(
        DIRegistrationError,
        match=r"^\[paths='/', handler='one', dependencies='value'\] Parameter 'headers' of provider .*provide_value "
        r".* is not marked as a dependency",
    ):
        Litestar([one], openapi_config=None)


def test_provider_construction_error_names_handler_and_key() -> None:
    def provide_value() -> Generator[str, None, None]:
        yield "x"

    @get("/", dependencies={"value": Provide(provide_value)})
    async def one(value: NamedDependency[str]) -> str:
        return value

    with pytest.raises(
        DIRegistrationError,
        match=r"^\[paths='/', handler='one', dependencies='value'\] Callable .*provide_value .* of type sync "
        r"generator function is not supported",
    ):
        Litestar([one], openapi_config=None)


def test_provider_construction_error_names_chain_of_keys_provider_is_reached_through() -> None:
    def provide_inner() -> Generator[str, None, None]:
        yield "x"

    async def provide_outer(inner: NamedDependency[str]) -> str:
        return inner

    @get("/", dependencies={"outer": Provide(provide_outer), "inner": Provide(provide_inner)})
    async def one(outer: NamedDependency[str]) -> str:
        return outer

    with pytest.raises(
        DIRegistrationError,
        match=r"^\[paths='/', handler='one', dependencies='inner' -> 'outer'\] Callable .*provide_inner .* of type "
        r"sync generator function is not supported",
    ):
        Litestar([one], openapi_config=None)


@pytest.mark.parametrize("layer", ["app", "router", "controller", "handler"])
def test_sequence_of_providers_at_layer_reaches_handler(layer: str) -> None:
    async def provide_name() -> str:
        return "name"

    async def provide_number() -> int:
        return 1

    by_layer = {layer: [Provider(provide_name, key="name"), Provider(provide_number, key="number")]}

    class ItemController(Controller):
        path = "/items"
        dependencies = by_layer.get("controller")

        @get(dependencies=by_layer.get("handler"))
        async def handler(self, name: NamedDependency[str], number: NamedDependency[int]) -> list[Any]:
            return [name, number]

    router = Router("/router", route_handlers=[ItemController], dependencies=by_layer.get("router"))

    with create_test_client([router], dependencies=by_layer.get("app")) as client:
        assert client.get("/router/items").json() == ["name", 1]


def test_sequence_of_providers_at_websocket_listener_reaches_listener() -> None:
    async def provide_name() -> str:
        return "name"

    @websocket_listener("/", dependencies=[Provider(provide_name, key="name")])
    async def handler(data: str, name: NamedDependency[str]) -> str:
        return f"{data} {name}"

    with create_test_client([handler]) as client, client.websocket_connect("/") as ws:
        ws.send_text("hello")
        assert ws.receive_text() == "hello name"


@pytest.mark.parametrize(
    "declare",
    [
        pytest.param(lambda key, fn: [Provider(fn, kind="type")], id="provider-in-sequence"),
        pytest.param(lambda key, fn: {key: Provider(fn, kind="type")}, id="provider-in-mapping"),
        pytest.param(lambda key, fn: {key: Provide(fn)}, id="provide-in-mapping"),
        pytest.param(lambda key, fn: {key: fn}, id="callable-in-mapping"),
    ],
)
def test_dependency_under_type_key_is_injected_by_type(declare: Any) -> None:
    class Config:
        name = "config"

    async def provide_config() -> Config:
        return Config()

    @get("/")
    async def handler(config: TypeDependency[Config]) -> str:
        return config.name

    with create_test_client([handler], dependencies=declare(Config, provide_config)) as client:
        assert client.get("/").text == "config"


def test_handler_mapping_overrides_app_sequence_provider_under_type_key() -> None:
    class Config:
        def __init__(self, name: str) -> None:
            self.name = name

    async def provide_app_config() -> Config:
        return Config("app")

    async def provide_handler_config() -> Config:
        return Config("handler")

    @get("/", dependencies={Config: Provider(provide_handler_config, kind="type")})
    async def handler(config: TypeDependency[Config]) -> str:
        return config.name

    with create_test_client([handler], dependencies=[Provider(provide_app_config, kind="type")]) as client:
        assert client.get("/").text == "handler"


def test_handler_sequence_overrides_app_mapping_provider_under_type_key() -> None:
    class Config:
        def __init__(self, name: str) -> None:
            self.name = name

    async def provide_app_config() -> Config:
        return Config("app")

    async def provide_handler_config() -> Config:
        return Config("handler")

    @get("/", dependencies=[Provider(provide_handler_config, kind="type")])
    async def handler(config: TypeDependency[Config]) -> str:
        return config.name

    with create_test_client([handler], dependencies={Config: Provider(provide_app_config, kind="type")}) as client:
        assert client.get("/").text == "handler"


def test_provider_under_other_mapping_key_raises() -> None:
    async def provide_value() -> int:
        return 1

    @get("/")
    async def handler(db: NamedDependency[int]) -> None: ...

    with pytest.raises(
        DIRegistrationError,
        match=r"^\[paths='/', handler='handler', dependencies='db'\] Provider .*\.provide_value \(.*\) has the key "
        r"'other', but is declared under the key 'db'$",
    ):
        Litestar([handler], dependencies={"db": Provider(provide_value, key="other")}, openapi_config=None)


def test_provider_under_other_type_mapping_key_raises() -> None:
    class Config:
        pass

    class OtherConfig:
        pass

    async def provide_other_config() -> OtherConfig:
        return OtherConfig()

    @get("/")
    async def handler(config: TypeDependency[Config]) -> None: ...

    with pytest.raises(
        DIRegistrationError,
        match=r"^\[paths='/', handler='handler', dependencies=.*\.Config\] Provider .*\.provide_other_config \(.*\) "
        r"has the key .*\.OtherConfig, but is declared under the key .*\.Config$",
    ):
        Litestar([handler], dependencies={Config: Provider(provide_other_config, kind="type")}, openapi_config=None)


def test_two_providers_under_one_key_in_sequence_raise() -> None:
    async def provide_value() -> int:
        return 1

    async def provide_other_value() -> int:
        return 2

    with pytest.raises(
        DIRegistrationError,
        match=r"^Cannot register provider .*\.provide_other_value \(.*\) for key 'value'\. The sequence of "
        r"dependencies already holds a provider for this key: .*\.provide_value \(.*\)$",
    ):
        Litestar(
            dependencies=[Provider(provide_value, key="value"), Provider(provide_other_value, key="value")],
            openapi_config=None,
        )


def test_plugin_writes_dependencies_of_app_given_sequence() -> None:
    async def provide_name() -> str:
        return "name"

    async def provide_number() -> int:
        return 1

    async def provide_flag() -> bool:
        return True

    class Plugin(InitPlugin):
        def on_app_init(self, app_config: AppConfig) -> AppConfig:
            app_config.dependencies["number"] = Provider(provide_number, key="number")
            app_config.dependencies.update({"flag": provide_flag})
            return app_config

    @get("/")
    async def handler(
        name: NamedDependency[str], number: NamedDependency[int], flag: NamedDependency[bool]
    ) -> list[Any]:
        return [name, number, flag]

    with create_test_client([handler], dependencies=[Provider(provide_name, key="name")], plugins=[Plugin()]) as client:
        assert client.get("/").json() == ["name", 1, True]


def test_provider_under_state_class_a_handler_depends_on_raises() -> None:
    async def provide_state() -> State:
        return State()

    @get("/")
    async def handler(state: State) -> None: ...

    with pytest.raises(
        DIRegistrationError,
        match=r"Cannot register provider .*\.provide_state \(.*\) at registry .* for key State\. "
        r"Another provider is already registered for this key: _provide_state \(.*\)\.",
    ):
        Litestar([handler], dependencies=[Provider(provide_state, kind="type")], openapi_config=None)


def test_setup_prepares_request_and_handler_context() -> None:
    @get("/")
    async def handler() -> None: ...

    app = Litestar([handler], openapi_config=None)

    setup = app.route_handler_method_map["/"]["GET"]._injection_setup
    assert (setup.request_context.registry, setup.request_context.scope) == (setup.registry, "request")
    assert (setup.handler_context.registry, setup.handler_context.scope) == (setup.registry, "handler")
