from functools import partial

from litestar.utils.helpers import unique_name_for_scope, unwrap_partial


def test_unwrap_partial() -> None:
    def func(*args: int) -> int:
        return sum(args)

    wrapped = partial(partial(partial(func, 1), 2))

    assert wrapped() == 3
    assert unwrap_partial(wrapped) is func


def test_unique_name_for_scope() -> None:
    assert unique_name_for_scope("a", []) == "a_0"

    assert unique_name_for_scope("a", ["a", "a_0", "b"]) == "a_1"

    assert unique_name_for_scope("b", ["a", "a_0", "b"]) == "b_0"
