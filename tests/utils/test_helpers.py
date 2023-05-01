from functools import partial

from litestar import Litestar
from litestar.utils.helpers import get_fqdn, unwrap_partial


def test_unwrap_partial() -> None:
    def func(*args: int) -> int:
        return sum(args)

    wrapped = partial(partial(partial(func, 1), 2))

    assert wrapped() == 3
    assert unwrap_partial(wrapped) is func


def test_get_fqdn() -> None:
    assert get_fqdn(Litestar) == "litestar.app.Litestar"
