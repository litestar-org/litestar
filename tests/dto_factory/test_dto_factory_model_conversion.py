import sys
import warnings
from datetime import datetime
from typing import Any, Callable, Dict, List

import pytest
from polyfactory.factories.pydantic_factory import ModelFactory

from starlite.contrib.tortoise_orm import TortoiseORMPlugin
from starlite.dto import DTOFactory
from starlite.exceptions import ImproperlyConfiguredException
from tests import Person, TypedDictPerson, VanillaDataClassPerson
from tests.contrib.tortoise_orm import Tournament


def _get_attribute_value(model_instance: Any, key: str) -> Any:
    """Utility to support getting values from a class instance, or dict."""
    try:
        return model_instance.__getattribute__(key)
    except AttributeError:
        return model_instance[key]


@pytest.mark.parametrize(
    "model, exclude, field_mapping, plugins",
    [
        [Person, [], {"complex": "ultra"}, []],
        [VanillaDataClassPerson, [], {"complex": "ultra"}, []],
        [TypedDictPerson, [], {"complex": "ultra"}, []],
    ],
)
def test_conversion_to_model_instance(model: Any, exclude: list, field_mapping: dict, plugins: list) -> None:
    MyDTO = DTOFactory(plugins=plugins)("MyDTO", model, exclude=exclude, field_mapping=field_mapping)

    class DTOModelFactory(ModelFactory[MyDTO]):  # type: ignore
        __model__ = MyDTO
        __allow_none_optionals__ = False

    dto_instance = DTOModelFactory.build()
    model_instance = dto_instance.to_model_instance()  # type: ignore

    for key in dto_instance.__fields__:  # type: ignore
        if key not in MyDTO.dto_field_mapping:
            attribute_value = _get_attribute_value(model_instance, key)
            assert attribute_value == dto_instance.__getattribute__(key)  # type: ignore
        else:
            original_key = MyDTO.dto_field_mapping[key]
            attribute_value = _get_attribute_value(model_instance, original_key)
            assert attribute_value == dto_instance.__getattribute__(key)  # type: ignore


@pytest.mark.skipif(sys.version_info < (3, 9), reason="dataclasses behave differently in lower versions")
@pytest.mark.parametrize(
    "model, exclude, field_mapping, plugins",
    [
        [Person, ["id"], {"complex": "ultra"}, []],
        [VanillaDataClassPerson, ["id"], {"complex": "ultra"}, []],
        [TypedDictPerson, ["id"], {"complex": "ultra"}, []],
    ],
)
def test_conversion_from_model_instance(
    model: Any, exclude: List[Any], field_mapping: Dict[str, Any], plugins: List[Any]
) -> None:
    DTO = DTOFactory(plugins=plugins)("MyDTO", model, exclude=exclude, field_mapping=field_mapping)

    model_instance = model(
        first_name="moishe",
        last_name="zuchmir",
        id="1",
        optional="some-value",
        complex={"key": [{"key": "value"}]},
        pets=None,
    )
    dto_instance = DTO.from_model_instance(model_instance=model_instance)
    for key in dto_instance.__fields__:
        if key not in DTO.dto_field_mapping:
            assert _get_attribute_value(model_instance, key) == _get_attribute_value(dto_instance, key)
        else:
            original_key = DTO.dto_field_mapping[key]
            assert _get_attribute_value(model_instance, original_key) == _get_attribute_value(dto_instance, key)


async def test_async_conversion_from_model_instance(scaffold_tortoise: Callable, anyio_backend: str) -> None:
    DTO = DTOFactory(plugins=[TortoiseORMPlugin()])("TournamentDTO", Tournament)

    tournament = Tournament(name="abc", id=1, created_at=datetime.now())

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with pytest.raises(ImproperlyConfiguredException):
            DTO.from_model_instance(tournament)

    dto_instance = await DTO.from_model_instance_async(tournament)
    assert dto_instance.name == "abc"  # type: ignore
    assert dto_instance.id == 1  # type: ignore


def test_sqlalchemy_jsonb_column() -> None:
    ...
