from os import urandom
from string import printable
from typing import TYPE_CHECKING

import pytest
from hypothesis import given
from hypothesis.strategies import (
    booleans,
    dictionaries,
    floats,
    lists,
    none,
    recursive,
    text,
)
from pydantic import SecretBytes, ValidationError

from starlite.middleware.session import (
    CHUNK_SIZE,
    SessionCookieConfig,
    SessionMiddleware,
)

if TYPE_CHECKING:
    from starlette.types import Receive, Scope, Send


async def mock_asgi_app(scope: "Scope", receive: "Receive", send: "Send") -> None:
    pass


json = recursive(
    none() | booleans() | floats() | text(printable),
    lambda children: lists(children) | dictionaries(text(printable), children),
)


@pytest.mark.parametrize(
    "secret, should_raise",
    [
        [urandom(16), False],
        [urandom(24), False],
        [urandom(32), False],
        [urandom(17), True],
        [urandom(4), True],
        [urandom(100), True],
        [b"", True],
    ],
)
def test_config_validation(secret: bytes, should_raise: bool) -> None:
    if should_raise:
        with pytest.raises(ValidationError):
            SessionCookieConfig(secret=SecretBytes(secret))
    else:
        SessionCookieConfig(secret=SecretBytes(secret))


@given(data=json)
@pytest.mark.parametrize("secret", [urandom(16), urandom(24), urandom(32)])
def test_dump_and_load_data(data: dict, secret: bytes) -> None:
    config = SessionCookieConfig(secret=SecretBytes(secret))
    middleware = SessionMiddleware(app=mock_asgi_app, config=config)

    dumped_list = middleware.dump_data(data)
    assert dumped_list

    for el in dumped_list:
        assert len(el) <= CHUNK_SIZE

    loaded_data = middleware.load_data(dumped_list)
    assert loaded_data == data
