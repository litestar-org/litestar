from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from starlite import HttpMethod, create_test_request
from tests.utils import Person


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
)
def test_create_test_request(http_method, scheme, server, port, root_path, path, query, headers, cookie, content):
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
    )
