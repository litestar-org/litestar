from typing import Any

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from starlite import HttpMethod, RequestEncodingType, Starlite, State, get
from starlite.datastructures import Cookie
from starlite.testing import TestClient, create_test_request
from tests import Person


@settings(suppress_health_check=HealthCheck.all())
@given(
    http_method=st.sampled_from(HttpMethod),
    scheme=st.text(),
    server=st.text(),
    port=st.integers(),
    root_path=st.text(),
    path=st.text(),
    query=st.one_of(
        st.none(),
        st.dictionaries(keys=st.text(), values=st.one_of(st.lists(st.text()), st.text())),
    ),
    headers=st.one_of(st.none(), st.dictionaries(keys=st.text(), values=st.text())),
    cookie=st.one_of(st.none(), st.text()),
    content=st.one_of(
        st.none(),
        st.builds(Person),
        st.dictionaries(keys=st.text(), values=st.builds(dict)),
    ),
    request_media_type=st.sampled_from(RequestEncodingType),
)
def test_create_test_request(
    http_method: Any,
    scheme: Any,
    server: Any,
    port: Any,
    root_path: Any,
    path: Any,
    query: Any,
    headers: Any,
    cookie: Any,
    content: Any,
    request_media_type: Any,
) -> None:
    create_test_request(
        http_method=http_method,
        scheme=scheme,
        server=server,
        port=port,
        root_path=root_path,
        path=path,
        query=query,
        headers=headers,
        cookie=cookie,
        content=content,
        request_media_type=request_media_type,
    )


def test_test_client() -> None:
    def start_up_handler(state: State) -> None:
        state.value = 1

    @get(path="/test")
    def test_handler(state: State) -> None:
        assert state.value == 1

    app = Starlite(route_handlers=[test_handler], on_startup=[start_up_handler])

    with TestClient(app=app) as client:
        client.get("/test")
        assert app.state.value == 1


def test_create_test_request_with_cookies(session_test_cookies: str) -> None:
    """Should accept either list of "Cookie" instance or as a string."""
    request = create_test_request(
        cookie=[Cookie(key="test", value="cookie"), Cookie(key="starlite", value="cookie", path="/test")]
    )
    cookies = request.cookies
    assert {"test", "starlite"}.issubset(cookies.keys())
    assert cookies["Path"] == "/test"

    request = create_test_request(cookie=session_test_cookies)
    assert "session-0" in request.cookies
