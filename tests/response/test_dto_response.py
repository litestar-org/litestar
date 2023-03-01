from sys import version_info
from typing import Any, Iterable, List, Tuple

import pytest

from starlite import get
from starlite.dto import DTOFactory
from starlite.status_codes import HTTP_200_OK
from starlite.testing import create_test_client
from tests import Person, PersonFactory

factory = DTOFactory()
PersonDTO = factory(name="PersonDTO", source=Person)


@pytest.mark.parametrize("data", (PersonFactory.build(), PersonFactory.build().dict()))
def test_dto_singleton_response(data: Any) -> None:
    @get("/")
    def handler() -> PersonDTO:  # type: ignore
        return data  # type: ignore

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert PersonDTO(**response.json())


if version_info >= (3, 10):
    py_310_plus_annotation = [
        (PersonFactory.batch(5), list[PersonDTO]),  # type: ignore
        ([p.dict() for p in PersonFactory.batch(5)], list[PersonDTO]),  # type: ignore
        (PersonFactory.batch(5), tuple[PersonDTO, ...]),  # type: ignore
        ([p.dict() for p in PersonFactory.batch(5)], tuple[PersonDTO, ...]),  # type: ignore
    ]
else:
    py_310_plus_annotation = []


@pytest.mark.parametrize(
    "data, annotation",
    (
        (PersonFactory.batch(0), List[PersonDTO]),  # type: ignore
        (PersonFactory.batch(5), List[PersonDTO]),  # type: ignore
        ([p.dict() for p in PersonFactory.batch(5)], List[PersonDTO]),  # type: ignore
        (PersonFactory.batch(5), Tuple[PersonDTO, ...]),
        ([p.dict() for p in PersonFactory.batch(5)], Tuple[PersonDTO, ...]),
        (PersonFactory.batch(5), Iterable[PersonDTO]),  # type: ignore
        ([p.dict() for p in PersonFactory.batch(5)], Iterable[PersonDTO]),  # type: ignore
        *py_310_plus_annotation,
    ),
)
def test_dto_list_response(data: Any, annotation: Any) -> None:
    @get("/")
    def handler() -> annotation:
        return data

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        results = [PersonDTO(**p) for p in response.json()]
        assert results == data
