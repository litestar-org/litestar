import pytest

from litestar import Litestar, post
from litestar.exceptions import LitestarDeprecationWarning
from litestar.params import Body, JSONBody


def test_deprecated_default_warns() -> None:
    @post("/")
    async def handler(data: JSONBody[dict] = Body()) -> None:
        pass

    with pytest.raises(LitestarDeprecationWarning, match=r"Deprecated use of 'Body\(\)' as a default value"):
        Litestar([handler])
