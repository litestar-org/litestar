from datetime import datetime, timedelta

from time_machine import travel

from litestar.datastructures import Cookie


def test_basic_cookie_as_header() -> None:
    cookie = Cookie(key="key")
    assert cookie.to_header() == 'Set-Cookie: key=""; Path=/; SameSite=lax'


@travel(datetime.utcnow, tick=False)
def test_cookie_as_header() -> None:
    expires_sec = 123
    cookie = Cookie(
        key="key",
        value="value",
        path="/path",
        expires=expires_sec,
        domain="domain.com",
        secure=True,
        httponly=True,
        samesite="strict",
    )

    now = datetime.utcnow()
    expected_expired = (now + timedelta(seconds=expires_sec)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    assert cookie.to_header() == (
        f"Set-Cookie: key=value; Domain=domain.com; expires={expected_expired}; HttpOnly; Path=/path; SameSite=strict; Secure"
    )


def test_cookie_with_max_age_as_header() -> None:
    cookie = Cookie(key="key", max_age=10)
    assert cookie.to_header() == 'Set-Cookie: key=""; Max-Age=10; Path=/; SameSite=lax'


def test_cookie_as_header_without_header_name() -> None:
    cookie = Cookie(key="key")
    assert cookie.to_header(header="") == 'key=""; Path=/; SameSite=lax'


def test_equality() -> None:
    assert Cookie(key="key") == Cookie(key="key")
    assert Cookie(key="key") != Cookie(key="key", path="/test")
    assert Cookie(key="key", path="/test") != Cookie(key="key", path="/test", domain="localhost")
    assert Cookie(key="key", path="/test", domain="localhost") == Cookie(key="key", path="/test", domain="localhost")
    assert Cookie(key="key") != "key"
