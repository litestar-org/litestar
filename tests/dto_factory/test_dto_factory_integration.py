import json
from typing import Any

import pytest
from polyfactory.factories.pydantic_factory import ModelFactory
from pydantic import BaseModel

from litestar import post
from litestar.dto import DTOFactory
from litestar.status_codes import HTTP_201_CREATED
from litestar.testing import create_test_client
from tests import Person, TypedDictPerson, VanillaDataClassPerson


@pytest.mark.parametrize(
    "model, exclude, field_mapping, plugins",
    [
        [Person, ["id"], {"complex": "ultra"}, []],
        [VanillaDataClassPerson, ["id"], {"complex": "ultra"}, []],
        [TypedDictPerson, ["id"], {"complex": "ultra"}, []],
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
        for k, v in data.dict().items():
            # the factory data might have datetime values in it which don't compare
            if k in ("sa_json", "my_json", "pg_json", "pg_jsonb", "sl_json"):
                dto_val = dto_instance[k]
                assert v == json.loads(json.dumps(dto_val, default=str))
            else:
                assert v == dto_instance[k]

    with create_test_client(route_handlers=[post_handler]) as client:
        post_response = client.post("/", content=json.dumps(dto_instance, default=str))
        assert post_response.status_code == HTTP_201_CREATED


@pytest.mark.parametrize(
    "model, exclude, field_mapping, field_definitions, plugins",
    [
        [Person, ["id"], {"complex": "ultra"}, {"special": (str, ...)}, []],
        [VanillaDataClassPerson, ["id"], {"complex": "ultra"}, {"special": (str, ...)}, []],
        [TypedDictPerson, ["id"], {"complex": "ultra"}, {"special": (str, ...)}, []],
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
