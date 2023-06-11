from typing import Any, List

import pytest
from typing_extensions import Annotated

from litestar import get, post
from litestar.di import Provide
from litestar.params import Body, Dependency, Parameter
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST
from litestar.testing import create_test_client


@pytest.mark.parametrize("backend", ("pydantic", "attrs"))
def test_parsing_of_parameter_as_annotated(backend: Any) -> None:
    @get(path="/")
    def handler(param: Annotated[str, Parameter(min_length=1)]) -> str:
        return param

    with create_test_client(handler, _preferred_validation_backend=backend) as client:
        response = client.get("/")
        assert response.status_code == HTTP_400_BAD_REQUEST

        response = client.get("/?param=a")
        assert response.status_code == HTTP_200_OK


@pytest.mark.parametrize("backend", ("pydantic", "attrs"))
def test_parsing_of_parameter_as_default_value(backend: Any) -> None:
    @get(path="/")
    def handler(param: str = Parameter(min_length=1)) -> str:
        return param

    with create_test_client(handler, _preferred_validation_backend=backend) as client:
        response = client.get("/?param=")
        assert response.status_code == HTTP_400_BAD_REQUEST

        response = client.get("/?param=a")
        assert response.status_code == HTTP_200_OK


@pytest.mark.parametrize("backend", ("pydantic", "attrs"))
def test_parsing_of_body_as_annotated(backend: Any) -> None:
    @post(path="/")
    def handler(data: Annotated[List[str], Body(min_items=1)]) -> List[str]:
        return data

    with create_test_client(handler, _preferred_validation_backend=backend) as client:
        response = client.post("/", json=[])
        assert response.status_code == HTTP_400_BAD_REQUEST

        response = client.post("/", json=["a"])
        assert response.status_code == HTTP_201_CREATED


@pytest.mark.parametrize("backend", ("pydantic", "attrs"))
def test_parsing_of_body_as_default_value(backend: Any) -> None:
    @post(path="/")
    def handler(data: List[str] = Body(min_items=1)) -> List[str]:
        return data

    with create_test_client(handler, _preferred_validation_backend=backend) as client:
        response = client.post("/", json=[])
        assert response.status_code == HTTP_400_BAD_REQUEST

        response = client.post("/", json=["a"])
        assert response.status_code == HTTP_201_CREATED


@pytest.mark.parametrize("backend", ("pydantic", "attrs"))
def test_parsing_of_dependency_as_annotated(backend: Any) -> None:
    @get(path="/", dependencies={"dep": Provide(lambda: None, sync_to_thread=False)})
    def handler(dep: Annotated[int, Dependency(skip_validation=True)]) -> int:
        return dep

    with create_test_client(handler, _preferred_validation_backend=backend) as client:
        response = client.get("/")
        assert response.text == "null"


@pytest.mark.parametrize("backend", ("pydantic", "attrs"))
def test_parsing_of_dependency_as_default_value(backend: Any) -> None:
    @get(path="/", dependencies={"dep": Provide(lambda: None, sync_to_thread=False)})
    def handler(dep: int = Dependency(skip_validation=True)) -> int:
        return dep

    with create_test_client(handler, _preferred_validation_backend=backend) as client:
        response = client.get("/")
        assert response.text == "null"
