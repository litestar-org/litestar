from functools import partial

from litestar.utils.helpers import unwrap_partial


def test_unwrap_partial() -> None:
    def func(*args: int) -> int:
        return sum(args)

    wrapped = partial(partial(partial(func, 1), 2))

    assert wrapped() == 3
    assert unwrap_partial(wrapped) is func
