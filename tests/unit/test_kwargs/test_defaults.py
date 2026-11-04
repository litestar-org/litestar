from typing import Annotated, Any, Optional

import pytest

from litestar import Litestar, get
from litestar.di import NamedDependency, Provide
from litestar.exceptions import ImproperlyConfiguredException
from litestar.params import QueryParameter
from litestar.status_codes import HTTP_200_OK, HTTP_400_BAD_REQUEST
from litestar.testing import create_test_client


def test_params_default() -> None:
    test_path = "/test"

    @get(path=test_path)
    def test_method(
        page_size: Annotated[int, QueryParameter(name="pageSize", gt=0, le=100)] = 10,
    ) -> None:
        assert page_size

    with create_test_client(test_method) as client:
        response = client.get(f"{test_path}?pageSize=10")
        assert response.status_code == HTTP_200_OK

        response = client.get(f"{test_path}")
        assert response.status_code == HTTP_200_OK


@pytest.mark.parametrize("annotation", [Optional[int], Any])
def test_missing_parameter_without_default(annotation: Any) -> None:
    @get("/", sync_to_thread=False)
    def handler(value: Annotated[annotation, QueryParameter()]) -> None:  # pyright: ignore[reportInvalidTypeForm]
        return None

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.status_code == HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Missing required query parameter 'value' for path /"


def test_optional_parameter_required_with_default() -> None:
    @get("/", sync_to_thread=False)
    def handler(value: Annotated[Optional[int], QueryParameter(required=True)] = 1) -> None:
        return None

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.status_code == HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Missing required query parameter 'value' for path /"


def test_parameter_not_required_receives_default() -> None:
    @get("/", sync_to_thread=False)
    def handler(value: Annotated[int, QueryParameter(required=False)] = 3) -> int:
        return value

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.json() == 3


def test_parameter_not_required_without_default_raises() -> None:
    @get("/", sync_to_thread=False)
    def handler(value: Annotated[int, QueryParameter(required=False)]) -> None:
        return None

    with pytest.raises(
        ImproperlyConfiguredException,
        match=r"handler='handler'\] Parameter 'value' is not required but declares no default",
    ):
        Litestar([handler])


def test_dependency_parameter_not_required_without_default_raises() -> None:
    def provide_value(value: Annotated[int, QueryParameter(required=False)]) -> int:
        return value

    @get("/", sync_to_thread=False, dependencies={"provided": Provide(provide_value, sync_to_thread=False)})
    def handler(provided: NamedDependency[int]) -> None:
        return None

    with pytest.raises(
        ImproperlyConfiguredException,
        match=r"dependencies='provided'\] Parameter 'value' is not required but declares no default",
    ):
        Litestar([handler])
