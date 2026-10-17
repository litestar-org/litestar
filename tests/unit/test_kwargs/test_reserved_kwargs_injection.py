# pyright: reportUnnecessaryTypeIgnoreComment=false
import re
import warnings
from typing import Any, Dict, List, Optional, Type, cast
from unittest.mock import MagicMock, call

import msgspec
import msgspec.json
import pytest
from typing_extensions import Annotated

from litestar import (
    Controller,
    HttpMethod,
    Litestar,
    MediaType,
    Request,
    WebSocket,
    delete,
    get,
    patch,
    post,
    put,
    websocket,
)
from litestar.connection import ASGIConnection
from litestar.datastructures import Headers
from litestar.datastructures.state import ImmutableState, State
from litestar.di import NamedDependency, Provide
from litestar.exceptions import ImproperlyConfiguredException, LitestarDeprecationWarning
from litestar.params import Dependency, FromPath, FromQuery, JSONBody, QueryParams, RawBody, RequestCookies
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
def test_application_state_injection(state_typing: Type[State]) -> None:
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
        def test_method(self, data: DataclassPerson) -> None:
            assert data == person_instance

    with pytest.warns(
        LitestarDeprecationWarning,
        match=re.escape(
            "Reserved kwarg 'data' declared without a body marker. Use 'data: JSONBody[DataclassPerson]' or another "
            "body marker instead. Reserved kwargs without their type will stop working in Litestar 3.0"
        ),
    ):
        client = create_test_client(MyController)

    with client:
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
        def test_method(self, data: List[DataclassPerson]) -> None:
            assert data == people

    with pytest.warns(
        LitestarDeprecationWarning,
        match=re.escape("Reserved kwarg 'data' declared without a body marker. Use 'data: JSONBody[List["),
    ):
        client = create_test_client(MyController)

    with client:
        response = client.request(http_method, test_path, json=msgspec.to_builtins(people))
        assert response.status_code == expected_status_code


@pytest.mark.parametrize("media_type", [MediaType.JSON, MediaType.MESSAGEPACK])
def test_request_with_invalid_data(media_type: MediaType) -> None:
    @post()
    def test_handler(data: JSONBody[Any]) -> Any:
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
        second: FromQuery[List[str]],
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
        def test_method(self, headers: dict) -> None:
            for key, value in request_headers.items():
                assert headers[key] == value

    with pytest.warns(
        LitestarDeprecationWarning,
        match=re.escape(
            "Reserved kwarg 'headers' declared as 'dict'. Use 'request.headers' instead. Reserved kwargs without "
            "their type will stop working in Litestar 3.0"
        ),
    ):
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
def test_body(decorator: Any, http_method: Any, expected_status_code: Any) -> None:
    test_path = "/person"

    class MyController(Controller):
        path = test_path

        @decorator()
        async def test_method(self, request: Request[Any, Any, Any], body: bytes) -> None:
            assert body == await request.body()

    with pytest.warns(
        LitestarDeprecationWarning,
        match=re.escape(
            "Reserved kwarg 'body' declared as 'bytes'. Declare it as 'body: RawBody' instead. Reserved kwargs "
            "without their type will stop working in Litestar 3.0"
        ),
    ):
        client = create_test_client(MyController)

    with client:
        response = client.request(http_method, test_path)
        assert response.status_code == expected_status_code


def test_headers_annotated_as_headers() -> None:
    @get("/")
    def handler(request: Request, headers: Headers) -> None:
        assert headers is request.headers

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK


def test_headers_annotated_differently_in_handler_and_dependency() -> None:
    def provide_value(request: Request, headers: Headers) -> str:
        assert headers is request.headers
        return "value"

    @get("/", dependencies={"value": Provide(provide_value, sync_to_thread=False)})
    def handler(headers: Dict[str, str], value: NamedDependency[str]) -> None:
        assert type(headers) is dict
        assert headers["x-a"] == "1"

    with pytest.warns(LitestarDeprecationWarning, match="Reserved kwarg 'headers' declared as 'Dict"):
        client = create_test_client(handler)

    with client:
        response = client.get("/", headers={"x-a": "1"})
        assert response.status_code == HTTP_200_OK


def test_query_annotated_as_query_params() -> None:
    @get("/")
    def handler(request: Request, query: QueryParams) -> None:
        assert query.dict() == request.query_params.dict()
        assert query.getall("a") == ["1", "2"]

    with create_test_client(handler) as client:
        response = client.get("/?a=1&a=2")
        assert response.status_code == HTTP_200_OK


def test_cookies_annotated_as_request_cookies() -> None:
    @get("/")
    def handler(cookies: RequestCookies) -> None:
        assert cookies == {"sid": "1"}

    with create_test_client(handler) as client:
        response = client.get("/", headers={"Cookie": "sid=1"})
        assert response.status_code == HTTP_200_OK


def test_body_annotated_as_raw_body() -> None:
    @post("/")
    async def handler(body: RawBody) -> None:
        assert body == b"raw"

    with create_test_client(handler) as client:
        response = client.post("/", content=b"raw")
        assert response.status_code == HTTP_201_CREATED


def test_untyped_reserved_kwargs_in_http_handler_warn() -> None:
    @get("/")
    async def handler(
        headers: Dict[str, str], query: Dict[str, Any], cookies: Dict[str, str], scope: Dict[str, Any]
    ) -> None: ...

    with pytest.warns(LitestarDeprecationWarning) as record:
        Litestar([handler])

    assert [str(warning.message) for warning in record] == [
        "[paths='/', handler='handler'] Reserved kwarg 'cookies' declared as 'Dict[str, str]'. Use "
        "'request.cookies' instead. Reserved kwargs without their type will stop working in Litestar 3.0",
        "[paths='/', handler='handler'] Reserved kwarg 'headers' declared as 'Dict[str, str]'. Use "
        "'request.headers' instead. Reserved kwargs without their type will stop working in Litestar 3.0",
        "[paths='/', handler='handler'] Reserved kwarg 'query' declared as 'Dict[str, Any]'. Use "
        "'request.query_params' instead. Reserved kwargs without their type will stop working in Litestar 3.0",
        "[paths='/', handler='handler'] Reserved kwarg 'scope' declared as 'Dict[str, Any]'. Use "
        "'request.scope' instead. Reserved kwargs without their type will stop working in Litestar 3.0",
    ]


def test_untyped_reserved_kwargs_in_websocket_handler_warn() -> None:
    @websocket("/")
    async def handler(
        socket: WebSocket,
        headers: Dict[str, str],
        query: Dict[str, Any],
        cookies: Dict[str, str],
        scope: Dict[str, Any],
    ) -> None: ...

    with pytest.warns(LitestarDeprecationWarning) as record:
        Litestar([handler])

    assert [str(warning.message) for warning in record] == [
        "[paths='/', handler='handler'] Reserved kwarg 'cookies' declared as 'Dict[str, str]'. Use "
        "'socket.cookies' instead. Reserved kwargs without their type will stop working in Litestar 3.0",
        "[paths='/', handler='handler'] Reserved kwarg 'headers' declared as 'Dict[str, str]'. Use "
        "'socket.headers' instead. Reserved kwargs without their type will stop working in Litestar 3.0",
        "[paths='/', handler='handler'] Reserved kwarg 'query' declared as 'Dict[str, Any]'. Use "
        "'socket.query_params' instead. Reserved kwargs without their type will stop working in Litestar 3.0",
        "[paths='/', handler='handler'] Reserved kwarg 'scope' declared as 'Dict[str, Any]'. Use "
        "'socket.scope' instead. Reserved kwargs without their type will stop working in Litestar 3.0",
    ]


def test_untyped_reserved_kwargs_in_dependency_warn() -> None:
    async def provide_value(
        headers: Dict[str, str],
        query: Dict[str, Any],
        cookies: Dict[str, str],
        scope: Dict[str, Any],
        body: bytes,
        data: DataclassPerson,
    ) -> str:
        return "value"

    @post("/", dependencies={"value": Provide(provide_value)})
    async def handler(value: NamedDependency[str]) -> None: ...

    with pytest.warns(LitestarDeprecationWarning) as record:
        Litestar([handler])

    assert [str(warning.message) for warning in record] == [
        "[paths='/', handler='handler', dependencies='value'] Reserved kwarg 'body' declared as 'bytes'. Declare "
        "it as 'body: RawBody' instead. Reserved kwargs without their type will stop working in Litestar 3.0",
        "[paths='/', handler='handler', dependencies='value'] Reserved kwarg 'cookies' declared as "
        "'Dict[str, str]'. Declare it as 'cookies: RequestCookies' instead. Reserved kwargs without their type "
        "will stop working in Litestar 3.0",
        "[paths='/', handler='handler', dependencies='value'] Reserved kwarg 'data' declared without a body "
        "marker. Use 'data: JSONBody[DataclassPerson]' or another body marker instead. Reserved kwargs without "
        "their type will stop working in Litestar 3.0",
        "[paths='/', handler='handler', dependencies='value'] Reserved kwarg 'headers' declared as "
        "'Dict[str, str]'. Declare it as 'headers: Headers' instead. Reserved kwargs without their type will "
        "stop working in Litestar 3.0",
        "[paths='/', handler='handler', dependencies='value'] Reserved kwarg 'query' declared as "
        "'Dict[str, Any]'. Declare it as 'query: QueryParams' instead. Reserved kwargs without their type will "
        "stop working in Litestar 3.0",
        "[paths='/', handler='handler', dependencies='value'] Reserved kwarg 'scope' declared as "
        "'Dict[str, Any]'. Declare it as 'scope: Scope' instead. Reserved kwargs without their type will stop "
        "working in Litestar 3.0",
    ]


def test_typed_reserved_kwargs_do_not_warn() -> None:
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

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        Litestar([handler])


@pytest.mark.parametrize("annotation, declared", [(Any, "Any"), (Dict[str, Any], "Dict[str, Any]")])
def test_request_kwarg_without_connection_type_warns(annotation: Any, declared: str) -> None:
    @get("/")
    async def handler(request: annotation) -> None: ...

    with pytest.warns(
        LitestarDeprecationWarning,
        match=re.escape(f"Reserved kwarg 'request' declared as '{declared}'. Declare it as 'request: Request'"),
    ):
        Litestar([handler])


def test_request_kwarg_typed_as_subclass_of_request_class_warns() -> None:
    @get("/")
    async def handler(request: CustomRequest) -> None: ...

    with pytest.warns(
        LitestarDeprecationWarning,
        match=re.escape("Reserved kwarg 'request' declared as 'CustomRequest'. Declare it as 'request: Request'"),
    ):
        Litestar([handler])


def test_request_kwarg_without_connection_type_names_custom_request_class() -> None:
    @get("/")
    async def handler(request: Any) -> None: ...

    with pytest.warns(
        LitestarDeprecationWarning,
        match=re.escape("Reserved kwarg 'request' declared as 'Any'. Declare it as 'request: CustomRequest'"),
    ):
        Litestar([handler], request_class=CustomRequest)


@pytest.mark.parametrize("annotation", [CustomRequest, Request, Request[Any, Any, Any], ASGIConnection])
def test_request_kwarg_typed_as_request_class_or_its_base_does_not_warn(annotation: Any) -> None:
    @get("/")
    async def handler(request: annotation) -> None: ...

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        Litestar([handler], request_class=CustomRequest)


def test_socket_kwarg_without_connection_type_warns() -> None:
    @websocket("/")
    async def handler(socket: Any) -> None: ...

    with pytest.warns(
        LitestarDeprecationWarning,
        match=re.escape("Reserved kwarg 'socket' declared as 'Any'. Declare it as 'socket: WebSocket'"),
    ):
        Litestar([handler])


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


def test_improper_use_of_state_kwarg_with_annotated_metadata() -> None:
    """``state`` typed as ``Annotated[<bad>, <KwargDefinition>]`` must surface the
    same configuration error as ``state: <bad>``. Previously the ``Annotated`` wrapper
    caused the subclass check to crash with ``TypeError`` before we could raise the
    configuration error.
    """
    from typing_extensions import Annotated

    from litestar.params import QueryParameter

    @get("/")
    async def handler(state: Annotated[str, QueryParameter(name="alias")]) -> None:
        return None

    with pytest.raises(ImproperlyConfiguredException):
        Litestar(route_handlers=[handler], openapi_config=None)


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
        async def test_method(self, data: JSONBody[DataclassPerson], person_name: Annotated[str, Dependency()]) -> None:
            assert data == person_instance
            assert person_name == f"{person_instance.first_name} {person_instance.last_name}"

    with create_test_client(MyController) as client:
        response = client.request(http_method, test_path, json=msgspec.to_builtins(person_instance))
        assert response.status_code == expected_status_code


def test_data_kwarg_in_dependency_only() -> None:
    mock = MagicMock()

    async def dependency_with_data(data: JSONBody[List[str]]) -> List[str]:
        mock(data)
        return data

    @post("/", dependencies={"some_data": dependency_with_data})
    def handler(some_data: NamedDependency[List[str]]) -> None:
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
    async def dependency_with_data(data: JSONBody[List[str]]) -> List[str]:
        return data

    @post("/", dependencies={"some_data": dependency_with_data})
    def handler(data: JSONBody[Dict[str, str]], some_data: NamedDependency[List[str]]) -> None:
        return None

    with pytest.raises(
        ImproperlyConfiguredException,
        match=re.escape("'data' fields have mismatched types: 'typing.Dict[str, str]' <> 'typing.List[str]'"),
    ):
        Litestar([handler])


def test_data_kwarg_type_mismatch_between_dependencies_raises() -> None:
    async def data_a(data: JSONBody[List[str]]) -> List[str]:
        return data

    async def data_b(data: JSONBody[Dict[str, str]]) -> Dict[str, str]:
        return data

    @post("/", dependencies={"a": data_a, "b": data_b})
    def handler(a: NamedDependency[Dict[str, str]], b: NamedDependency[List[str]]) -> None:
        return None

    with pytest.raises(
        ImproperlyConfiguredException,
        match=re.escape("'data' fields have mismatched types: 'typing.Dict[str, str]' <> 'typing.List[str]'"),
    ):
        Litestar([handler])
