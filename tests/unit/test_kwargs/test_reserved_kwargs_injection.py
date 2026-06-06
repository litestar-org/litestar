# pyright: reportUnnecessaryTypeIgnoreComment=false
import re
from typing import Annotated, Any, Optional, cast, List, Dict
from unittest.mock import MagicMock, call

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
)
from litestar.datastructures.state import ImmutableState, State
from litestar.di import NamedDependency, Provide
from litestar.exceptions import ImproperlyConfiguredException
from litestar.params import FromPath, FromQuery, JSONBody
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
        def test_method(self, data: list[DataclassPerson]) -> None:
            assert data == people

    with create_test_client(MyController) as client:
        response = client.request(http_method, test_path, json=msgspec.to_builtins(people))
        assert response.status_code == expected_status_code


@pytest.mark.parametrize("media_type", [MediaType.JSON, MediaType.MESSAGEPACK])
def test_request_with_invalid_data(media_type: MediaType) -> None:
    @post()
    def test_handler(data: Any) -> Any:
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
        def test_method(self, headers: dict) -> None:
            for key, value in request_headers.items():
                assert headers[key] == value

    with create_test_client(MyController) as client:
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

    with create_test_client(MyController) as client:
        response = client.request(http_method, test_path)
        assert response.status_code == expected_status_code


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

    async def dependency_with_data(data: DataclassPerson) -> str:
        assert isinstance(data, DataclassPerson)
        return f"{data.first_name} {data.last_name}"

    class MyController(Controller):
        path = test_path

        @decorator(dependencies={"person_name": Provide(dependency_with_data)})
        async def test_method(self, data: DataclassPerson, person_name: NamedDependency[str]) -> None:
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
    async def dependency_with_data(data: JSONBody[List[str]]) -> List[str]:
        return data

    @post("/", dependencies={"some_data": dependency_with_data})
    def handler(data: JSONBody[Dict[str, str]], some_data: NamedDependency[List[str]]) -> None:
        return None

    with pytest.raises(
        ImproperlyConfiguredException,
        match=re.escape("'data' fields have mismatched types: 'dict[str, str]' <> 'list[str]'"),
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
        match=re.escape("'data' fields have mismatched types: 'dict[str, str]' <> 'list[str]'"),
    ):
        Litestar([handler])
