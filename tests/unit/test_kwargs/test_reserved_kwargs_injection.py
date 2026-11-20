# pyright: reportUnnecessaryTypeIgnoreComment=false
import re
from collections.abc import Callable
from typing import Annotated, Any, Optional, cast
from unittest.mock import MagicMock, call

import annotated_types
import msgspec.json
import pytest

from litestar import (
    Controller,
    HttpMethod,
    Litestar,
    MediaType,
    Request,
    delete,
    get,
    patch,
    post,
    put,
    websocket,
)
from litestar.connection import ASGIConnection, WebSocket
from litestar.datastructures import Headers
from litestar.datastructures.state import ImmutableState, State
from litestar.di import NamedDependency, Provide
from litestar.di.exceptions import DIRegistrationError, MissingProviderError
from litestar.exceptions import ImproperlyConfiguredException, LitestarDeprecationWarning
from litestar.params import FromPath, FromQuery, JSONBody, MsgPackBody, QueryParams, RawBody, RequestCookies
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
)
from litestar.testing import TestClient, create_test_client
from litestar.types import Scope
from tests.models import DataclassPerson, DataclassPersonFactory


class CustomState(State):
    called: bool
    msg: str


class CustomRequest(Request):
    pass


def test_application_immutable_state_injection() -> None:
    @get("/", media_type=MediaType.TEXT)
    def route_handler(state: ImmutableState) -> str:
        assert state
        return cast("str", state.msg)

    with create_test_client(route_handler, state=State({"called": False})) as client:
        client.app.state.msg = "hello"
        assert not client.app.state.called
        response = client.get("/")
        assert response.status_code == HTTP_200_OK


@pytest.mark.parametrize("state_typing", (State, CustomState))
def test_application_state_injection(state_typing: type[State]) -> None:
    @get("/", media_type=MediaType.TEXT)
    def route_handler(state: state_typing) -> str:  # type: ignore[valid-type]
        assert state
        state.called = True  # type: ignore[attr-defined]
        return cast("str", state.msg)  # type: ignore[attr-defined]

    with create_test_client(route_handler, state=State({"called": False})) as client:
        client.app.state.msg = "hello"
        assert not client.app.state.called
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.text == "hello"
        assert client.app.state.called


def test_state_subclass_in_cached_dependency() -> None:
    async def provide_msg(state: CustomState) -> str:
        return state.msg

    @get("/", media_type=MediaType.TEXT, dependencies={"msg": Provide(provide_msg, use_cache=True)})
    def handler(msg: NamedDependency[str]) -> str:
        return msg

    with create_test_client(handler, state=State({"msg": "hello"})) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.text == "hello"


@pytest.mark.parametrize("state_class", (State, CustomState, ImmutableState))
def test_state_reflects_change_to_app_state(state_class: type[ImmutableState]) -> None:
    @get("/", media_type=MediaType.TEXT)
    def handler(state: state_class) -> str:  # type: ignore[valid-type]
        return cast("str", state.msg)  # type: ignore[attr-defined]

    with create_test_client(handler, state=State({"msg": "one"})) as client:
        assert client.get("/").text == "one"
        client.app.state.msg = "two"
        assert client.get("/").text == "two"


person_instance = DataclassPersonFactory.build()


@pytest.mark.parametrize(
    "decorator, http_method, expected_status_code",
    [
        (post, HttpMethod.POST, HTTP_201_CREATED),
        (put, HttpMethod.PUT, HTTP_200_OK),
        (patch, HttpMethod.PATCH, HTTP_200_OK),
        (delete, HttpMethod.DELETE, HTTP_204_NO_CONTENT),
    ],
)
def test_data_using_model(decorator: Any, http_method: Any, expected_status_code: Any) -> None:
    test_path = "/person"

    class MyController(Controller):
        path = test_path

        @decorator()
        def test_method(self, data: JSONBody[DataclassPerson]) -> None:
            assert data == person_instance

    with create_test_client(MyController) as client:
        response = client.request(http_method, test_path, json=msgspec.to_builtins(person_instance))
        assert response.status_code == expected_status_code


@pytest.mark.parametrize(
    "decorator, http_method, expected_status_code",
    [
        (post, HttpMethod.POST, HTTP_201_CREATED),
        (put, HttpMethod.PUT, HTTP_200_OK),
        (patch, HttpMethod.PATCH, HTTP_200_OK),
        (delete, HttpMethod.DELETE, HTTP_204_NO_CONTENT),
    ],
)
def test_data_using_list_of_models(decorator: Any, http_method: Any, expected_status_code: Any) -> None:
    test_path = "/person"

    people = DataclassPersonFactory.batch(size=5)

    class MyController(Controller):
        path = test_path

        @decorator()
        def test_method(self, data: JSONBody[list[DataclassPerson]]) -> None:
            assert data == people

    with create_test_client(MyController) as client:
        response = client.request(http_method, test_path, json=msgspec.to_builtins(people))
        assert response.status_code == expected_status_code


@pytest.mark.parametrize("media_type, body_marker", [(MediaType.JSON, JSONBody), (MediaType.MESSAGEPACK, MsgPackBody)])
def test_request_with_invalid_data(media_type: MediaType, body_marker: Any) -> None:
    @post()
    def test_handler(data: body_marker[Any]) -> Any:  # pyright: ignore
        return data

    with create_test_client(test_handler) as client:
        response = client.post("/", content=b"abc", headers={"Content-Type": media_type})
        assert response.status_code == HTTP_400_BAD_REQUEST


@pytest.mark.parametrize(
    "decorator, http_method, expected_status_code",
    [
        (get, HttpMethod.GET, HTTP_200_OK),
        (post, HttpMethod.POST, HTTP_201_CREATED),
        (put, HttpMethod.PUT, HTTP_200_OK),
        (patch, HttpMethod.PATCH, HTTP_200_OK),
        (delete, HttpMethod.DELETE, HTTP_204_NO_CONTENT),
    ],
)
def test_path_params(decorator: Any, http_method: Any, expected_status_code: Any) -> None:
    test_path = "/person"

    class MyController(Controller):
        path = test_path

        @decorator(path="/{person_id:str}")
        def test_method(self, person_id: FromPath[str]) -> None:
            assert person_id == person_instance.id

    with create_test_client(MyController) as client:
        response = client.request(http_method, f"{test_path}/{person_instance.id}")
        assert response.status_code == expected_status_code


@pytest.mark.parametrize(
    "decorator, http_method, expected_status_code",
    [
        (get, HttpMethod.GET, HTTP_200_OK),
        (post, HttpMethod.POST, HTTP_201_CREATED),
        (put, HttpMethod.PUT, HTTP_200_OK),
        (patch, HttpMethod.PATCH, HTTP_200_OK),
        (delete, HttpMethod.DELETE, HTTP_204_NO_CONTENT),
    ],
)
def test_query_params(decorator: Any, http_method: Any, expected_status_code: Any) -> None:
    @decorator("/person")
    def handler(
        first: FromQuery[str],
        second: FromQuery[list[str]],
        third: FromQuery[int],
        fourth: FromQuery[Optional[str]] = None,
    ) -> None:
        assert first == "foo"
        assert second == ["a", "b"]
        assert third == 2
        assert fourth is None

    with create_test_client(handler) as client:
        response = client.request(http_method, "/person", params={"first": "foo", "second": ["a", "b"], "third": "2"})
        assert response.status_code == expected_status_code


@pytest.mark.parametrize(
    "decorator, http_method, expected_status_code",
    [
        (get, HttpMethod.GET, HTTP_200_OK),
        (post, HttpMethod.POST, HTTP_201_CREATED),
        (put, HttpMethod.PUT, HTTP_200_OK),
        (patch, HttpMethod.PATCH, HTTP_200_OK),
        (delete, HttpMethod.DELETE, HTTP_204_NO_CONTENT),
    ],
)
def test_header_params(decorator: Any, http_method: Any, expected_status_code: Any) -> None:
    test_path = "/person"

    request_headers = {
        "application-type": "web",
        "site": "www.example.com",
        "user-agent": "some-thing",
        "accept": "*/*",
    }

    class MyController(Controller):
        path = test_path

        @decorator()
        def test_method(self, headers: Headers) -> None:
            for key, value in request_headers.items():
                assert headers[key] == value

    with pytest.warns(LitestarDeprecationWarning, match="'Headers', which is deprecated"):
        client = create_test_client(MyController)
    with client:
        response = client.request(http_method, test_path, headers=request_headers)
        assert response.status_code == expected_status_code


@pytest.mark.parametrize(
    "decorator, http_method, expected_status_code",
    [
        (get, HttpMethod.GET, HTTP_200_OK),
        (post, HttpMethod.POST, HTTP_201_CREATED),
        (put, HttpMethod.PUT, HTTP_200_OK),
        (patch, HttpMethod.PATCH, HTTP_200_OK),
        (delete, HttpMethod.DELETE, HTTP_204_NO_CONTENT),
    ],
)
def test_request(decorator: Any, http_method: Any, expected_status_code: Any) -> None:
    test_path = "/person"

    class MyController(Controller):
        path = test_path

        @decorator()
        def test_method(self, request: Request) -> None:
            assert isinstance(request, Request)

    with create_test_client(MyController) as client:
        response = client.request(http_method, test_path)
        assert response.status_code == expected_status_code


@pytest.mark.parametrize(
    "decorator, http_method, expected_status_code",
    [
        (get, HttpMethod.GET, HTTP_200_OK),
        (post, HttpMethod.POST, HTTP_201_CREATED),
        (put, HttpMethod.PUT, HTTP_200_OK),
        (patch, HttpMethod.PATCH, HTTP_200_OK),
        (delete, HttpMethod.DELETE, HTTP_204_NO_CONTENT),
    ],
)
def test_scope(decorator: Any, http_method: Any, expected_status_code: Any) -> None:
    test_path = "/person"

    class MyController(Controller):
        path = test_path

        @decorator()
        def test_method(self, scope: Scope) -> None:
            assert isinstance(scope, dict)

    with pytest.warns(LitestarDeprecationWarning, match="'Scope', which is deprecated"):
        client = create_test_client(MyController)
    with client:
        response = client.request(http_method, test_path)
        assert response.status_code == expected_status_code


@pytest.mark.parametrize(
    "decorator, http_method, expected_status_code",
    [
        (post, HttpMethod.POST, HTTP_201_CREATED),
        (put, HttpMethod.PUT, HTTP_200_OK),
        (patch, HttpMethod.PATCH, HTTP_200_OK),
        (delete, HttpMethod.DELETE, HTTP_204_NO_CONTENT),
    ],
)
def test_body(decorator: Any, http_method: Any, expected_status_code: Any) -> None:
    test_path = "/person"

    class MyController(Controller):
        path = test_path

        @decorator()
        async def test_method(self, request: Request[Any, Any, Any], body: RawBody) -> None:
            assert body == await request.body()

    with create_test_client(MyController) as client:
        response = client.request(http_method, test_path)
        assert response.status_code == expected_status_code


def test_headers_annotated_as_headers() -> None:
    @get("/")
    def handler(request: Request, headers: Headers) -> None:
        assert headers is request.headers

    with pytest.warns(LitestarDeprecationWarning, match="'Headers', which is deprecated"):
        client = create_test_client(handler)
    with client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK


def test_query_annotated_as_query_params() -> None:
    @get("/")
    def handler(request: Request, query: QueryParams) -> None:
        assert query.dict() == request.query_params.dict()
        assert query.getall("a") == ["1", "2"]

    with pytest.warns(LitestarDeprecationWarning, match="'QueryParams', which is deprecated"):
        client = create_test_client(handler)
    with client:
        response = client.get("/?a=1&a=2")
        assert response.status_code == HTTP_200_OK


def test_cookies_annotated_as_request_cookies() -> None:
    @get("/")
    def handler(cookies: RequestCookies) -> None:
        assert cookies == {"sid": "1"}

    with pytest.warns(LitestarDeprecationWarning, match="'RequestCookies', which is deprecated"):
        client = create_test_client(handler)
    with client:
        response = client.get("/", headers={"Cookie": "sid=1"})
        assert response.status_code == HTTP_200_OK


def test_body_annotated_as_raw_body() -> None:
    @post("/")
    async def handler(body: RawBody) -> None:
        assert body == b"raw"

    with create_test_client(handler) as client:
        response = client.post("/", content=b"raw")
        assert response.status_code == HTTP_201_CREATED


def test_untyped_reserved_kwargs_in_http_handler_raise() -> None:
    @get("/")
    async def with_cookies(cookies: dict[str, str]) -> None: ...

    @get("/")
    async def with_headers(headers: dict[str, str]) -> None: ...

    @get("/")
    async def with_query(query: dict[str, Any]) -> None: ...

    @get("/")
    async def with_scope(scope: dict[str, Any]) -> None: ...

    @post("/")
    async def with_body(body: bytes) -> None: ...

    @post("/")
    async def with_data(data: DataclassPerson) -> None: ...

    @post("/")
    async def with_constrained_data(data: Annotated[int, annotated_types.Gt(0)]) -> None: ...

    for handler, message in [
        (with_cookies, "Missing declaration for parameter 'cookies'"),
        (with_headers, "Missing declaration for parameter 'headers'"),
        (with_query, "Missing declaration for parameter 'query'"),
        (with_scope, "Missing declaration for parameter 'scope'"),
        (with_body, "Missing declaration for parameter 'body'"),
        (with_data, "Missing declaration for parameter 'data'"),
        (with_constrained_data, "Missing declaration for parameter 'data'"),
    ]:
        with pytest.raises(ImproperlyConfiguredException) as exc_info:
            Litestar([handler])
        assert exc_info.value.detail == f"[paths='/', handler={handler.handler_name!r}] {message}"


def test_untyped_reserved_kwargs_in_websocket_handler_raise() -> None:
    @websocket("/")
    async def with_cookies(socket: WebSocket, cookies: dict[str, str]) -> None: ...

    @websocket("/")
    async def with_headers(socket: WebSocket, headers: dict[str, str]) -> None: ...

    @websocket("/")
    async def with_query(socket: WebSocket, query: dict[str, Any]) -> None: ...

    @websocket("/")
    async def with_scope(socket: WebSocket, scope: dict[str, Any]) -> None: ...

    for handler, message in [
        (with_cookies, "Missing declaration for parameter 'cookies'"),
        (with_headers, "Missing declaration for parameter 'headers'"),
        (with_query, "Missing declaration for parameter 'query'"),
        (with_scope, "Missing declaration for parameter 'scope'"),
    ]:
        with pytest.raises(ImproperlyConfiguredException) as exc_info:
            Litestar([handler])
        assert exc_info.value.detail == f"[paths='/', handler={handler.handler_name!r}] {message}"


def test_untyped_reserved_kwargs_in_dependency_raise() -> None:
    async def with_cookies(cookies: dict[str, str]) -> str:
        return "value"

    async def with_headers(headers: dict[str, str]) -> str:
        return "value"

    async def with_query(query: dict[str, Any]) -> str:
        return "value"

    async def with_scope(scope: dict[str, Any]) -> str:
        return "value"

    async def with_body(body: bytes) -> str:
        return "value"

    async def with_data(data: DataclassPerson) -> str:
        return "value"

    async def with_constrained_data(data: Annotated[int, annotated_types.Gt(0)]) -> str:
        return "value"

    cases: list[tuple[Callable[..., Any], str]] = [
        (
            with_cookies,
            r"\[paths='/', handler='handler', dependencies='value'\] Parameter 'cookies' of provider .*with_cookies .* "
            "is not marked as a dependency",
        ),
        (
            with_headers,
            r"\[paths='/', handler='handler', dependencies='value'\] Parameter 'headers' of provider .*with_headers .* "
            "is not marked as a dependency",
        ),
        (
            with_query,
            r"\[paths='/', handler='handler', dependencies='value'\] Parameter 'query' of provider .*with_query .* "
            "is not marked as a dependency",
        ),
        (
            with_scope,
            r"\[paths='/', handler='handler', dependencies='value'\] Parameter 'scope' of provider .*with_scope .* "
            "is not marked as a dependency",
        ),
        (
            with_body,
            r"\[paths='/', handler='handler', dependencies='value'\] Parameter 'body' of provider .*with_body .* "
            "is not marked as a dependency",
        ),
        (
            with_data,
            r"\[paths='/', handler='handler', dependencies='value'\] Parameter 'data' of provider .*with_data .* "
            "is not marked as a dependency",
        ),
        (
            with_constrained_data,
            r"\[paths='/', handler='handler', dependencies='value'\] Parameter 'data' of provider "
            ".*with_constrained_data .* is not marked as a dependency",
        ),
    ]
    for provider, message in cases:

        @post("/", dependencies={"value": Provide(provider)})
        async def handler(value: NamedDependency[str]) -> None: ...

        with pytest.raises(DIRegistrationError, match=message):
            Litestar([handler])


def test_typed_reserved_kwargs_do_not_raise() -> None:
    async def provide_value(
        request: Request,
        headers: Headers,
        query: QueryParams,
        cookies: RequestCookies,
        scope: Scope,
        body: RawBody,
        data: JSONBody[DataclassPerson],
    ) -> str:
        return "value"

    @post("/", dependencies={"value": Provide(provide_value)})
    async def handler(
        request: Request,
        headers: Headers,
        query: QueryParams,
        cookies: RequestCookies,
        scope: Scope,
        body: RawBody,
        data: JSONBody[DataclassPerson],
        value: NamedDependency[str],
    ) -> None: ...

    with pytest.warns(LitestarDeprecationWarning, match="which are deprecated"):
        Litestar([handler])


class Item:
    pass


# a class from a user module that happens to be named 'typing'
Item.__module__, Item.__qualname__ = "myapp.typing", "Item"


@pytest.mark.parametrize("annotation", [Any, dict[str, Any], list[Item]])
def test_request_kwarg_without_connection_type_raises(annotation: Any) -> None:
    @get("/")
    async def handler(request: annotation) -> None: ...  # pyright: ignore

    with pytest.raises(ImproperlyConfiguredException, match=re.escape("Missing declaration for parameter 'request'")):
        Litestar([handler])


def test_request_kwarg_typed_as_subclass_of_request_class_raises() -> None:
    @get("/")
    async def handler(request: CustomRequest) -> None: ...

    with pytest.raises(MissingProviderError, match="has no provider for dependency CustomRequest"):
        Litestar([handler])


def test_request_kwarg_without_connection_type_raises_under_custom_request_class() -> None:
    @get("/")
    async def handler(request: Any) -> None: ...

    with pytest.raises(ImproperlyConfiguredException, match=re.escape("Missing declaration for parameter 'request'")):
        Litestar([handler], request_class=CustomRequest)


@pytest.mark.parametrize("annotation", [CustomRequest, Request, Request[Any, Any, Any], ASGIConnection])
def test_request_kwarg_typed_as_request_class_or_its_base_does_not_raise(annotation: Any) -> None:
    @get("/")
    async def handler(request: annotation) -> None: ...  # pyright: ignore

    Litestar([handler], request_class=CustomRequest)


def test_socket_kwarg_without_connection_type_raises() -> None:
    @websocket("/")
    async def handler(socket: Any) -> None: ...

    with pytest.raises(ImproperlyConfiguredException, match=re.escape("Missing declaration for parameter 'socket'")):
        Litestar([handler])


@pytest.mark.parametrize("name", ["request", "scope", "headers", "query", "cookies", "state", "socket", "data", "body"])
@pytest.mark.parametrize(
    "annotation, handler_path, url",
    [
        pytest.param(FromQuery[int], "/", "/?{name}=3", id="query"),
        pytest.param(FromPath[int], "/{{{name}:int}}", "/3", id="path"),
    ],
)
def test_marked_parameter_named_like_reserved_value_is_request_parameter(
    name: str, annotation: Any, handler_path: str, url: str
) -> None:
    namespace: dict[str, Any] = {"__name__": __name__, "annotation": annotation}
    exec(f"async def handler({name}: annotation) -> int:\n    return {name}", namespace)

    with create_test_client([get(handler_path.format(name=name))(namespace["handler"])]) as client:
        response = client.get(url.format(name=name))

    assert response.json() == 3


@pytest.mark.parametrize("name", ["request", "scope", "headers", "query", "cookies", "state", "socket", "data", "body"])
def test_dependency_key_named_like_reserved_value_is_dependency(name: str) -> None:
    async def provide_value() -> int:
        return 3

    namespace: dict[str, Any] = {"__name__": __name__, "NamedDependency": NamedDependency}
    exec(f"async def handler({name}: NamedDependency[int]) -> int:\n    return {name}", namespace)

    with create_test_client([get("/", dependencies={name: provide_value})(namespace["handler"])]) as client:
        response = client.get("/")

    assert response.json() == 3


def test_improper_use_of_state_kwarg() -> None:
    """Test the error condition of State kwarg with an unexpected type."""
    test_path = "/bad-state"

    class MyController(Controller):
        path = test_path

        @get()
        async def test_method(self, state: str) -> None:
            return None

    with pytest.raises(ImproperlyConfiguredException):
        Litestar(route_handlers=[MyController], openapi_config=None)


def test_websocket_handler_declares_socket_under_other_name() -> None:
    @websocket("/")
    async def handler(connection: WebSocket) -> None:
        await connection.accept()
        await connection.send_text("hello")
        await connection.close()

    with create_test_client([handler]) as client, client.websocket_connect("/") as ws:
        assert ws.receive_text() == "hello"


def test_websocket_handler_without_parameters_builds() -> None:
    @websocket("/")
    async def handler() -> None: ...

    Litestar([handler], openapi_config=None)


@pytest.mark.parametrize(
    "decorator, http_method, expected_status_code",
    [
        (post, HttpMethod.POST, HTTP_201_CREATED),
        (put, HttpMethod.PUT, HTTP_200_OK),
        (patch, HttpMethod.PATCH, HTTP_200_OK),
        (delete, HttpMethod.DELETE, HTTP_204_NO_CONTENT),
    ],
)
def test_data_kwarg_in_dependency(decorator: Any, http_method: Any, expected_status_code: Any) -> None:
    """Test that using 'data' kwarg in a dependency function doesn't raise KeyError.

    This test addresses GitHub issue #4230 where using the 'data' reserved kwarg
    in a dependency function would cause a KeyError during application initialization.
    """
    test_path = "/person"

    async def dependency_with_data(data: JSONBody[DataclassPerson]) -> str:
        assert isinstance(data, DataclassPerson)
        return f"{data.first_name} {data.last_name}"

    class MyController(Controller):
        path = test_path

        @decorator(dependencies={"person_name": Provide(dependency_with_data)})
        async def test_method(self, data: JSONBody[DataclassPerson], person_name: NamedDependency[str]) -> None:
            assert data == person_instance
            assert person_name == f"{person_instance.first_name} {person_instance.last_name}"

    with create_test_client(MyController) as client:
        response = client.request(http_method, test_path, json=msgspec.to_builtins(person_instance))
        assert response.status_code == expected_status_code


def test_data_kwarg_in_dependency_only() -> None:
    mock = MagicMock()

    async def dependency_with_data(data: JSONBody[list[str]]) -> list[str]:
        mock(data)
        return data

    @post("/", dependencies={"some_data": dependency_with_data})
    def handler(some_data: NamedDependency[list[str]]) -> None:
        mock(some_data)
        return

    app = Litestar([handler])
    assert app.openapi_schema.paths["/"].post.request_body.to_schema() == {  # type: ignore[union-attr, index]
        "content": {"application/json": {"schema": {"items": {"type": "string"}, "type": "array"}}},
        "required": True,
    }

    with TestClient(app) as client:
        res = client.post("/", json=["1", "2"])
        assert res.status_code == 201
        mock.assert_has_calls([call(["1", "2"]), call(["1", "2"])])

        res = client.post("/", json={"foo": "bar"})
        assert res.status_code == 400


def test_data_kwarg_type_mismatch_between_handler_and_dependency_raises() -> None:
    async def dependency_with_data(data: JSONBody[list[str]]) -> list[str]:
        return data

    @post("/", dependencies={"some_data": dependency_with_data})
    def handler(data: JSONBody[dict[str, str]], some_data: NamedDependency[list[str]]) -> None:
        return None

    with pytest.raises(
        ImproperlyConfiguredException,
        match=re.escape(
            "parameter 'data' of handler 'handler' and parameter 'data' of provider 'some_data' declare the "
            "request body differently: type 'dict[str, str]' and type 'list[str]'"
        ),
    ):
        Litestar([handler])


def test_data_kwarg_type_mismatch_between_dependencies_raises() -> None:
    async def data_a(data: JSONBody[list[str]]) -> list[str]:
        return data

    async def data_b(data: JSONBody[dict[str, str]]) -> dict[str, str]:
        return data

    @post("/", dependencies={"a": data_a, "b": data_b})
    def handler(a: NamedDependency[dict[str, str]], b: NamedDependency[list[str]]) -> None:
        return None

    with pytest.raises(
        ImproperlyConfiguredException,
        match=re.escape(
            "parameter 'data' of provider 'a' and parameter 'data' of provider 'b' declare the request body "
            "differently: type 'list[str]' and type 'dict[str, str]'"
        ),
    ):
        Litestar([handler])
