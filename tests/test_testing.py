from typing import Any

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from starlite import HttpMethod, RequestEncodingType, create_test_request
from tests import Person


@settings(suppress_health_check=HealthCheck.all())  # type: ignore[misc]
@given(  # type: ignore[misc]
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
