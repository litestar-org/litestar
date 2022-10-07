from typing import Any

from pydantic import BaseModel
from typing_extensions import get_args

from starlite.plugins.sql_alchemy import SQLAlchemyPlugin
from tests.plugins.sql_alchemy_plugin import Pet, User


def test_relationship() -> None:
    result = SQLAlchemyPlugin().to_pydantic_model_class(model_class=User)  # type:ignore[arg-type]
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
    pet_table = Pet
    user_table = User
    assert pet_table.__tablename__ == "pet"
    assert user_table.__tablename__ == "user"
