from hypothesis import given
from hypothesis import strategies as st
from pydantic import BaseModel

from starlite import HttpMethod, create_test_request


class Model(BaseModel):
    prop: str


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
    content=st.one_of(
        st.none(),
        st.builds(Model),
        st.dictionaries(keys=st.text(), values=st.builds(dict)),
    ),
)
def test_create_test_request(http_method, scheme, server, port, root_path, path, query, headers, content):
    create_test_request(
        http_method=http_method,
        scheme=scheme,
        server=server,
        port=port,
        root_path=root_path,
        path=path,
        query=query,
        headers=headers,
        content=content,
    )
