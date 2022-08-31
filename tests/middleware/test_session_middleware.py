import secrets
import time
from os import urandom
from typing import TYPE_CHECKING, Dict
from unittest import mock

import pytest
from pydantic import SecretBytes, ValidationError

from starlite import DefineMiddleware, Request, get
from starlite.middleware.session import (
    CHUNK_SIZE,
    SessionCookieConfig,
    SessionMiddleware,
)
from starlite.testing import create_test_client

if TYPE_CHECKING:
    from starlette.types import Receive, Scope, Send

TEST_SECRET = SecretBytes(urandom(16))


async def mock_asgi_app(scope: "Scope", receive: "Receive", send: "Send") -> None:
    pass


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


@pytest.fixture(autouse=True)
def session_middleware() -> SessionMiddleware:
    return SessionMiddleware(app=mock_asgi_app, config=SessionCookieConfig(secret=TEST_SECRET))


def create_session(size: int = 16) -> Dict[str, str]:
    return {"key": secrets.token_hex(size)}


@pytest.mark.parametrize("session", [create_session(), create_session(size=4096)])
def test_dump_and_load_data(session: dict, session_middleware: SessionMiddleware) -> None:
    ciphertext = session_middleware.dump_data(session)
    assert isinstance(ciphertext, list)

    for text in ciphertext:
        assert len(text) <= CHUNK_SIZE

    plain_text = session_middleware.load_data(ciphertext)
    assert plain_text == session


@mock.patch("time.time", return_value=round(time.time()))
def test_load_data_should_return_empty_if_session_expired(
    time_mock: mock.MagicMock, session_middleware: SessionMiddleware
) -> None:
    """Should return empty dict if session is expired."""
    ciphertext = session_middleware.dump_data(create_session())
    time_mock.return_value = round(time.time()) + session_middleware.config.max_age + 1
    plaintext = session_middleware.load_data(data=ciphertext)
    assert plaintext == {}


def test_set_session_cookies() -> None:
    """Should set session cookies from session in response."""
    chunks_multiplier = 2

    @get(path="/")
    def handler(request: Request) -> None:
        # Create large session by keeping it multiple of CHUNK_SIZE. This will split the session into multiple cookies.
        # Then you only need to check if number of cookies set are more than the multiplying number.
        request.session.update(create_session(size=CHUNK_SIZE * chunks_multiplier))

    client = create_test_client(
        route_handlers=[handler],
        middleware=[DefineMiddleware(SessionMiddleware, config=SessionCookieConfig(secret=TEST_SECRET))],
    )

    response = client.get("/")
    assert len(response.cookies) > chunks_multiplier
    # If it works for the multiple chunks of session, it works for the single chunk too. So, just check if "session-0"
    # exists.
    assert "session-0" in response.cookies


@pytest.mark.parametrize("mutate", [False, True])
def test_load_session_cookies_and_expire_previous(mutate: bool, session_middleware: SessionMiddleware) -> None:
    """Should load session cookies into session from request and overwrite the
    previously set cookies with the upcoming response.

    Session cookies from the previous session should not persist because
    session is mutable. Once the session is loaded from the cookies,
    those cookies are redundant. The response sets new session cookies
    overwriting or expiring the previous ones.
    """
    # Test for large session data. If it works for multiple cookies, it works for single also.
    _session = create_session(size=4096)

    @get(path="/")
    def handler(request: Request) -> dict:
        nonlocal _session
        if mutate:
            # Modify the session, this will overwrite the previously set session cookies.
            request.session.update(create_session())
            _session = request.session
        return request.session

    ciphertext = session_middleware.dump_data(_session)

    client = create_test_client(
        route_handlers=[handler],
        middleware=[DefineMiddleware(SessionMiddleware, config=SessionCookieConfig(secret=TEST_SECRET))],
    )

    response = client.get(
        "/",
        cookies={
            f"{session_middleware.config.key}-{i}": text.decode("utf-8") for i, text in enumerate(ciphertext, start=0)
        },
    )

    assert response.json() == _session
    # The session cookie names that were in the request will also be present in its response to overwrite or to expire
    # them. So, the number of cookies in the response will be at least equal to or greater than the number of cookies
    # that were in the request.
    assert response.headers["set-cookie"].count("session") >= response.request.headers["Cookie"].count("session")
