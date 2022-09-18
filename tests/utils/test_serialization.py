from pathlib import PosixPath
from typing import Any

import pytest
from pydantic import SecretStr

from starlite.utils.serialization import default_serializer
from tests import PersonFactory

person = PersonFactory.build()


@pytest.mark.parametrize(
    "value, expected, should_raise",
    [[person, person.dict(), False], [SecretStr("abc"), "abc", False], [PosixPath("/"), "/", False], [1, 1, True]],
)
def test_default_serializer(value: Any, expected: Any, should_raise: bool) -> None:
    if should_raise:
        with pytest.raises(TypeError):
            default_serializer(value)
    else:
        assert default_serializer(value) == expected
