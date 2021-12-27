from starlite.types import Partial
from tests import Person

try:
    from typing import _UnionGenericAlias as GenericAlias  # type: ignore
except ImportError:
    from typing import _GenericAlias as GenericAlias  # type: ignore


def test_partial():
    partial = Partial[Person]
    assert partial
    for field in partial.__fields__.values():
        assert field.allow_none
        assert not field.required
    for field in partial.__annotations__.values():
        assert isinstance(field, GenericAlias)
        assert type(None) in field.__args__
