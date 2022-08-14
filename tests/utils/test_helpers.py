import sys
from typing import Any, Dict

import pytest

from starlite.utils import is_class_and_subclass


class C:
    pass


@pytest.mark.skipif(sys.version_info < (3, 9), reason="requires python3.9 or higher")
def test_is_class_and_subclass_builtin_generic_collection() -> None:
    assert is_class_and_subclass(dict[str, Any], C) is False


def test_is_class_and_subclass_typing_generic_collection() -> None:
    assert is_class_and_subclass(Dict[str, Any], C) is False


def test_is_class_and_subclass_instance() -> None:
    assert is_class_and_subclass(C(), C) is False


def test_is_class_and_subclass() -> None:
    class Sub(C):
        ...

    assert is_class_and_subclass(Sub, C) is True
