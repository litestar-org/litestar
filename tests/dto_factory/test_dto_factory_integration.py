from typing import Any

import pytest
from pydantic import BaseModel
from pydantic_factories import ModelFactory
from starlette.status import HTTP_200_OK, HTTP_201_CREATED

from starlite import DTOFactory, get, post
from starlite.plugins.sql_alchemy import SQLAlchemyPlugin
from starlite.testing import create_test_client
from tests import Person, VanillaDataClassPerson
from tests.plugins.sql_alchemy_plugin import Pet


@pytest.mark.parametrize(
    "model, exclude, field_mapping, plugins",
    [
        [Person, ["id"], {"complex": "ultra"}, []],
        [VanillaDataClassPerson, ["id"], {"complex": "ultra"}, []],
        [Pet, ["owner"], {"species": "kind"}, [SQLAlchemyPlugin()]],
    ],
)
def test_dto_integration(model: Any, exclude: list, field_mapping: dict, plugins: list) -> None:
    MyDTO = DTOFactory(plugins=plugins)("MyDTO", model, exclude=exclude, field_mapping=field_mapping)

    class DTOModelFactory(ModelFactory[MyDTO]):  # type: ignore
        __model__ = MyDTO

    dto_instance = DTOModelFactory.build().dict()  # type: ignore

    @post(path="/")
    def post_handler(data: MyDTO) -> None:  # type: ignore
        assert isinstance(data, MyDTO)
        assert data == dto_instance

    @get(path="/")
    def get_handler() -> Any:
        return dto_instance

    with create_test_client(route_handlers=[post_handler, get_handler]) as client:
        post_response = client.post("/", json=dto_instance)
        assert post_response.status_code == HTTP_201_CREATED
        get_response = client.get("/")
        assert get_response.status_code == HTTP_200_OK
        assert get_response.json() == dto_instance


@pytest.mark.parametrize(
    "model, exclude, field_mapping, field_definitions, plugins",
    [
        [Person, ["id"], {"complex": "ultra"}, {"special": (str, ...)}, []],
        [VanillaDataClassPerson, ["id"], {"complex": "ultra"}, {"special": (str, ...)}, []],
        [Pet, ["age"], {"species": "kind"}, {"special": (str, ...)}, [SQLAlchemyPlugin()]],
    ],
)
def test_dto_factory(model: Any, exclude: list, field_mapping: dict, field_definitions: dict, plugins: list) -> None:
    dto = DTOFactory(plugins=plugins)(
        "MyDTO", model, exclude=exclude, field_mapping=field_mapping, field_definitions=field_definitions
    )
    assert issubclass(dto, BaseModel)
    assert dto.__name__ == "MyDTO"
    assert not any(excluded_key in dto.__fields__ for excluded_key in exclude)
    assert all(remapped_key in dto.__fields__ for remapped_key in field_mapping.values())
    special = dto.__fields__["special"]
    assert not special.allow_none
    assert special.type_ is str
