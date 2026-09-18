import os
import secrets
import time
from base64 import b64decode, b64encode
from typing import Any
from unittest import mock

import pytest
from cryptography.exceptions import InvalidTag

from litestar import Request, get, post
from litestar.datastructures.headers import MutableScopeHeaders
from litestar.exceptions import ImproperlyConfiguredException
from litestar.middleware.session import SessionMiddleware
from litestar.middleware.session.client_side import (
    AAD,
    CHUNK_SIZE,
    MAX_COOKIE_SIZE,
    ClientSideSessionBackend,
    CookieBackendConfig,
)
from litestar.serialization import encode_json
from litestar.testing import RequestFactory, create_test_client
from litestar.types.asgi_types import HTTPResponseStartEvent
from tests.helpers import RANDOM


@pytest.mark.parametrize(
    "secret, should_raise",
    [
        [RANDOM.randbytes(16), False],
        [RANDOM.randbytes(24), False],
        [RANDOM.randbytes(32), False],
        [RANDOM.randbytes(17), True],
        [RANDOM.randbytes(4), True],
        [RANDOM.randbytes(100), True],
        [b"", True],
    ],
)
def test_secret_validation(secret: bytes, should_raise: bool) -> None:
    if should_raise:
        with pytest.raises(ImproperlyConfiguredException):
            CookieBackendConfig(secret=secret)
    else:
        CookieBackendConfig(secret=secret)


@pytest.mark.parametrize(
    "key, should_raise",
    [
        ["", True],
        ["a", False],
        ["a" * 256, False],
        ["a" * 257, True],
    ],
)
def test_key_validation(key: str, should_raise: bool) -> None:
    if should_raise:
        with pytest.raises(ImproperlyConfiguredException):
            CookieBackendConfig(secret=os.urandom(16), key=key)
    else:
        CookieBackendConfig(secret=os.urandom(16), key=key)


@pytest.mark.parametrize(
    "max_age, should_raise",
    [
        [0, True],
        [-1, True],
        [1, False],
        [100, False],
    ],
)
def test_max_age_validation(max_age: int, should_raise: bool) -> None:
    if should_raise:
        with pytest.raises(ImproperlyConfiguredException):
            CookieBackendConfig(secret=os.urandom(16), key="a", max_age=max_age)
    else:
        CookieBackendConfig(secret=os.urandom(16), key="a", max_age=max_age)


def create_session(size: int = 16) -> dict[str, str]:
    return {"key": secrets.token_hex(size)}


@pytest.mark.parametrize("session", [create_session(), create_session(size=4096)])
def test_dump_and_load_data(session: dict, cookie_session_backend: ClientSideSessionBackend) -> None:
    ciphertext = cookie_session_backend.dump_data(session)
    assert isinstance(ciphertext, list)

    for cookie in cookie_session_backend._create_session_cookies(ciphertext):
        assert len(cookie.to_header(header="")) <= MAX_COOKIE_SIZE

    plain_text = cookie_session_backend.load_data(ciphertext)
    assert plain_text == session


@mock.patch("time.time", return_value=round(time.time()))
def test_load_data_should_return_empty_if_session_expired(
    time_mock: mock.MagicMock, cookie_session_backend: ClientSideSessionBackend
) -> None:
    """Should return empty dict if session is expired."""
    ciphertext = cookie_session_backend.dump_data(create_session())
    time_mock.return_value = round(time.time()) + cookie_session_backend.config.max_age + 1
    plaintext = cookie_session_backend.load_data(data=ciphertext)
    assert plaintext == {}


def test_set_session_cookies(cookie_session_backend_config: "CookieBackendConfig") -> None:
    """Should set session cookies from session in response."""
    chunks_multiplier = 2

    @get(path="/test")
    def handler(request: Request) -> None:
        # Create large session by keeping it multiple of CHUNK_SIZE. This will split the session into multiple cookies.
        # Then you only need to check if number of cookies set are more than the multiplying number.
        request.session.update(create_session(size=CHUNK_SIZE * chunks_multiplier))

    @get(path="/test_short_cookie")
    def handler_short_cookie(request: Request) -> None:
        # Check the naming of a cookie that's short enough to not get broken into chunks
        request.session.update(create_session())

    with create_test_client(
        route_handlers=[handler],
        middleware=[cookie_session_backend_config.middleware],
    ) as client:
        response = client.get("/test")

        assert len(response.cookies) > chunks_multiplier
        assert "session-0" in response.cookies

    with create_test_client(
        route_handlers=[handler_short_cookie],
        middleware=[cookie_session_backend_config.middleware],
    ) as client:
        response = client.get("/test_short_cookie")

        assert len(response.cookies) == 1
        assert "session" in response.cookies


def test_session_cookie_name_matching(cookie_session_backend_config: "CookieBackendConfig") -> None:
    session_data = {"foo": "bar"}

    @get("/")
    def handler(request: Request) -> dict[str, Any]:
        return request.session

    @post("/")
    def set_session_data(request: Request) -> None:
        request.set_session(session_data)

    with create_test_client(
        route_handlers=[handler, set_session_data],
        middleware=[cookie_session_backend_config.middleware],
    ) as client:
        client.post("/")
        client.cookies[f"thisisnnota{cookie_session_backend_config.key}cookie"] = "foo"
        response = client.get("/")
        assert response.json() == session_data


@pytest.mark.parametrize("mutate", [False, True])
def test_load_session_cookies_and_expire_previous(
    mutate: bool, cookie_session_middleware: SessionMiddleware[ClientSideSessionBackend]
) -> None:
    """Should load session cookies into session from request and overwrite the previously set cookies with the upcoming
    response.

    Session cookies from the previous session should not persist because session is mutable. Once the session is loaded
    from the cookies, those cookies are redundant. The response sets new session cookies overwriting or expiring the
    previous ones.
    """
    # Test for large session data. If it works for multiple cookies, it works for single also.
    _session = create_session(size=4096)

    @get(path="/test")
    def handler(request: Request) -> dict:
        nonlocal _session
        if mutate:
            # Modify the session, this will overwrite the previously set session cookies.
            request.session.update(create_session())
            _session = request.session
        return request.session

    ciphertext = cookie_session_middleware.backend.dump_data(_session)

    with create_test_client(
        route_handlers=[handler],
        middleware=[cookie_session_middleware.backend.config.middleware],
    ) as client:
        # Set cookies on the client to avoid warnings about per-request cookies.
        client.cookies = {
            f"{cookie_session_middleware.backend.config.key}-{i}": text.decode("utf-8")
            for i, text in enumerate(ciphertext)
        }
        response = client.get("/test")

    assert response.json() == _session
    # The session cookie names that were in the request will also be present in its response to overwrite or to expire
    # them. So, the number of cookies in the response will be at least equal to or greater than the number of cookies
    # that were in the request.
    assert response.headers["set-cookie"].count("session") >= response.request.headers["Cookie"].count("session")


def test_load_data_should_raise_invalid_tag_if_tampered_aad(cookie_session_backend: ClientSideSessionBackend) -> None:
    """If AAD has been tampered with, the integrity of the data cannot be verified and InvalidTag exception is
    raised.
    """
    encrypted_session = cookie_session_backend.dump_data(create_session())
    # The attacker will tamper with the AAD to increase the expiry time of the cookie.
    attacker_chosen_time = 300  # In seconds
    fraudulent_associated_data = encode_json(
        {"expires_at": round(time.time()) + cookie_session_backend.config.max_age + attacker_chosen_time}
    )
    decoded = b64decode(b"".join(encrypted_session))
    aad_starts_from = decoded.find(AAD)
    # The attacker removes the original AAD and attaches its own.
    ciphertext = b64encode(decoded[:aad_starts_from] + AAD + fraudulent_associated_data)
    # The attacker puts the data back to its original form.
    encoded = [ciphertext[i : i + CHUNK_SIZE] for i in range(0, len(ciphertext), CHUNK_SIZE)]

    with pytest.raises(InvalidTag):
        cookie_session_backend.load_data(encoded)


def test_get_cookie_keys_are_ordered_by_chunk_index(cookie_session_backend: ClientSideSessionBackend) -> None:
    """Chunk cookies must be ordered by their numeric index, not by name.

    A lexicographic sort places ``session-10`` between ``session-1`` and ``session-2``, so the two orders
    only agree while there are fewer than ten chunks.
    """
    expected = [f"session-{i}" for i in range(12)]
    connection = RequestFactory().get("/", headers={"Cookie": "; ".join(f"{key}=x" for key in expected)})

    assert cookie_session_backend.get_cookie_keys(connection) == expected


@pytest.mark.parametrize("key", ["session", "my-session"])
def test_large_session_round_trips(key: str) -> None:
    """A session spread over more than ten cookies must be reassembled in the right order."""
    payload = "x" * 40_000

    @get("/set")
    def set_handler(request: Request) -> None:
        request.session["payload"] = payload

    @get("/get")
    def get_handler(request: Request) -> dict[str, Any]:
        return request.session

    config = CookieBackendConfig(secret=os.urandom(16), key=key)
    with create_test_client([set_handler, get_handler], middleware=[config.middleware]) as client:
        response = client.get("/set")
        # more than ten cookies, otherwise the ordering this asserts on is not exercised
        assert len(response.headers.get_list("set-cookie")) > 10

        assert client.get("/get").json() == {"payload": payload}


@pytest.mark.parametrize("session_size", [8, 3_000, 60_000])
@pytest.mark.parametrize(
    "cookie_params",
    [
        {},
        {"secure": True},
        {"secure": True, "domain": "example.com", "path": "/a/rather/long/path/segment"},
    ],
)
@pytest.mark.parametrize("key", ["session", "s" * 60, "k" * 250])
def test_session_cookies_do_not_exceed_max_cookie_size(
    key: str, cookie_params: dict[str, Any], session_size: int
) -> None:
    """Every emitted ``Set-Cookie`` header must stay within the :rfc:`6265` limit.

    The cookie name and its attributes count towards that limit, so the space left for the value depends
    on the configured key and cookie parameters.
    """

    @get("/")
    def handler(request: Request) -> None:
        request.session["payload"] = "x" * session_size

    config = CookieBackendConfig(secret=os.urandom(16), key=key, **cookie_params)
    with create_test_client([handler], middleware=[config.middleware]) as client:
        headers = client.get("/").headers.get_list("set-cookie")

    assert headers
    for header in headers:
        assert len(header) <= MAX_COOKIE_SIZE


def test_dump_data_raises_when_cookie_attributes_leave_no_room() -> None:
    """A configuration whose cookie name and attributes fill the entire size limit must fail loudly.

    Emitting no cookies at all would log every user out with nothing in the response, and nothing in the
    logs, to point at the cause.
    """
    config = CookieBackendConfig(secret=os.urandom(16), path="/" + "p" * MAX_COOKIE_SIZE)
    backend = ClientSideSessionBackend(config=config)

    with pytest.raises(ImproperlyConfiguredException, match="leaving no room for session data"):
        backend.dump_data(create_session())


async def test_store_in_message_clears_cookies_when_session_grows_gt_chunk_size(
    cookie_session_backend: ClientSideSessionBackend,
) -> None:
    """Should clear the cookies when the session grows larger than the chunk size."""
    # we have a connection that already contains a cookie header with the "session" key in it
    connection = RequestFactory().get("/", headers={"Cookie": "session=foo"})
    # we want to persist a new session that is larger than the chunk size
    # by the time the encrypted data, nonce and associated data are b64 encoded, the size of
    # this session will be > 2x larger than the chunk size
    session = create_session(size=CHUNK_SIZE)
    message: HTTPResponseStartEvent = {"type": "http.response.start", "status": 200, "headers": []}
    await cookie_session_backend.store_in_message(session, message, connection)
    # due to the large session stored in multiple chunks, we now enumerate the name of the cookies
    # e.g., session-0, session-1, session-2, etc. This means we need to have a cookie with the name
    # "session" in the response headers that is set to null to clear the original cookie.
    headers = MutableScopeHeaders.from_message(message)
    assert len(headers.headers) > 1
    header_name, header_content = headers.headers[-1]
    assert header_name == b"set-cookie"
    assert header_content.startswith(b"session=null;")
