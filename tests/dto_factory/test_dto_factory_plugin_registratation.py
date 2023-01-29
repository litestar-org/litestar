from typing import Any, Optional

import pytest

from starlite import DTOFactory
from starlite.plugins.sqlalchemy import SQLAlchemyPlugin
from tests import Person, TypedDictPerson, VanillaDataClassPerson
from tests.plugins.sqlalchemy_plugin import Activity, Pet


@pytest.mark.parametrize(
    "model, exclude, field_mapping, plugins, expected_dto_plugin",
    [
        [Person, [], {"complex": "ultra"}, [], None],
        [VanillaDataClassPerson, [], {"complex": "ultra"}, [], None],
        [TypedDictPerson, [], {"complex": "ultra"}, [], None],
        [Pet, ["age"], {"species": "kind"}, [SQLAlchemyPlugin()], SQLAlchemyPlugin],
        [Activity, [], {}, [SQLAlchemyPlugin()], SQLAlchemyPlugin],
    ],
)
def test_plugin_registration(
    model: Any, exclude: list, field_mapping: dict, plugins: list, expected_dto_plugin: Optional[type]
) -> None:
    MyDTO = DTOFactory(plugins=plugins)("MyDTO", model, exclude=exclude, field_mapping=field_mapping)

    if not expected_dto_plugin:
        assert not MyDTO.dto_source_plugin
        return

    assert isinstance(MyDTO.dto_source_plugin, expected_dto_plugin)
