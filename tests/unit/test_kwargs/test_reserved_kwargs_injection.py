from typing import Any, List, Optional, Type, cast

import pydantic
import pytest
from polyfactory.factories.pydantic_factory import ModelFactory
from pydantic import BaseModel, Field

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
from litestar.contrib.pydantic import _model_dump
from litestar.datastructures.state import ImmutableState, State
from litestar.exceptions import ImproperlyConfiguredException
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
)
from litestar.testing import create_test_client
from litestar.types import Scope
from tests import PydanticPerson, PydanticPersonFactory


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
def test_application_state_injection(state_typing: Type[State]) -> None:
    @get("/", media_type=MediaType.TEXT)
    def route_handler(state: state_typing) -> str:  # type: ignore
        assert state
        state.called = True  # type: ignore
        return cast("str", state.msg)  # type: ignore

    with create_test_client(route_handler, state=State({"called": False})) as client:
        client.app.state.msg = "hello"
        assert not client.app.state.called
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.text == "hello"
        assert client.app.state.called


class QueryParams(BaseModel):
    first: str
    second: List[str] = (
        Field(min_items=3) if pydantic.VERSION.startswith("1") else Field(min_length=1)  # pyright: ignore
    )
    third: Optional[int]


class QueryParamsFactory(ModelFactory):
    __model__ = QueryParams


person_instance = PydanticPersonFactory.build()


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
        def test_method(self, data: PydanticPerson) -> None:
            assert data == person_instance

    with create_test_client(MyController) as client:
        response = client.request(http_method, test_path, json=_model_dump(person_instance))
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

    people = PydanticPersonFactory.batch(size=5)

    class MyController(Controller):
        path = test_path

        @decorator()
        def test_method(self, data: List[PydanticPerson]) -> None:
            assert data == people

    with create_test_client(MyController) as client:
        response = client.request(http_method, test_path, json=[_model_dump(p) for p in people])
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
        def test_method(self, person_id: str) -> None:
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
    test_path = "/person"

    query_params_instance = QueryParamsFactory.build()

    class MyController(Controller):
        path = test_path

        @decorator()
        def test_method(self, first: str, second: List[str], third: Optional[int] = None) -> None:
            assert first == query_params_instance.first
            assert second == query_params_instance.second
            assert third == query_params_instance.third

    with create_test_client(MyController) as client:
        response = client.request(http_method, test_path, params=query_params_instance.dict(exclude_none=True))
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
    """Test error condition of State kwarg with unexpected type.."""
    test_path = "/bad-state"

    class MyController(Controller):
        path = test_path

        @get()
        async def test_method(self, state: str) -> None:
            return None

    with pytest.raises(ImproperlyConfiguredException):
        Litestar(route_handlers=[MyController], openapi_config=None)
