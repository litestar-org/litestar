from typing import Any

from pydantic import BaseModel
from typing_extensions import get_args

from starlite.plugins.sql_alchemy import SQLAlchemyPlugin
from tests.plugins.sql_alchemy_plugin import Company, Pet, User


def test_relationship() -> None:
    result = SQLAlchemyPlugin().to_data_container_class(model_class=User)  # type: ignore
    assert issubclass(result, BaseModel)
    result.update_forward_refs()
    fields = result.__fields__
    friends = fields["friends"]
    assert get_args(friends.outer_type_)  # we assert this is a List[]
    assert friends.type_ is result
    pets = fields["pets"]
    assert pets.outer_type_ is Any
    company = fields["company"]
    assert not get_args(company.outer_type_)
    assert issubclass(company.type_, BaseModel)


def test_table_name() -> None:
    assert Pet.__tablename__ == "pet"
    assert User.__tablename__ == "user"


def test_plugin_to_dict_with_relationship() -> None:
    plugin = SQLAlchemyPlugin()
    user = User(id=1, name="A. Person", company=Company(id=1, name="Mega Corp", worth=1.0))
    plugin.to_dict(user)  # type:ignore[arg-type]
