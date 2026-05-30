import dataclasses
import warnings
from typing import Any, Dict

import annotated_types
import pytest
from typing_extensions import Annotated

from litestar import Litestar, get
from litestar.di import NamedDependency
from litestar.enums import ParamType
from litestar.exceptions.base_exceptions import LitestarDeprecationWarning
from litestar.openapi.spec import Parameter as OpenAPIParameter
from litestar.params import (
    CookieParameter,
    Dependency,
    FromCookie,
    FromHeader,
    FromPath,
    FromQuery,
    HeaderParameter,
    Parameter,
    ParameterKwarg,
    PathParameter,
    QueryParameter,
)
from litestar.testing import TestClient, create_test_client


def _legacy_parameter(**kwargs: Any) -> ParameterKwarg:
    """Construct a deprecated 'Parameter()' kwarg, suppressing the construction-time
    deprecation warning so the call site can later test the kwargs_model deprecation
    warning in isolation.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return Parameter(**kwargs)  # type: ignore[no-any-return]


def test_simple_form_handler() -> None:
    @get("/{path_param:int}")
    def handler(
        path_param: FromPath[int],
        query_param: FromQuery[int],
        header_param: FromHeader[int],
        cookie_param: FromCookie[int],
    ) -> Dict[str, int]:
        return {"query": query_param, "header": header_param, "cookie": cookie_param, "path": path_param}

    with create_test_client([handler], raise_server_exceptions=True) as client:
        client.cookies.set("cookie_param", "4")
        res = client.get("/1?query_param=2", headers={"header_param": "3"})
        assert res.status_code == 200
        assert res.json() == {"path": 1, "query": 2, "header": 3, "cookie": 4}


def test_explicit_form_handler() -> None:
    @get("/{path_param:int}")
    def handler(
        path_param: Annotated[int, PathParameter()],
        query_param: Annotated[int, QueryParameter()],
        header_param: Annotated[int, HeaderParameter()],
        cookie_param: Annotated[int, CookieParameter()],
    ) -> Dict[str, int]:
        return {"query": query_param, "header": header_param, "cookie": cookie_param, "path": path_param}

    with create_test_client([handler], raise_server_exceptions=True) as client:
        client.cookies.set("cookie_param", "4")
        res = client.get("/1?query_param=2", headers={"header_param": "3"})
        assert res.status_code == 200
        assert res.json() == {"path": 1, "query": 2, "header": 3, "cookie": 4}


def test_explicit_form_with_alias_handler() -> None:
    @get("/{path_param:int}")
    def handler(
        path_p: Annotated[int, PathParameter(name="path_param")],
        query_p: Annotated[int, QueryParameter(name="query_param")],
        header_p: Annotated[int, HeaderParameter(name="header_param")],
        cookie_p: Annotated[int, CookieParameter(name="cookie_param")],
    ) -> Dict[str, int]:
        return {"query": query_p, "header": header_p, "cookie": cookie_p, "path": path_p}

    app = Litestar([handler])
    schema_params = app.openapi_schema.paths["/{path_param}"].get.parameters  # type: ignore[index, union-attr]

    assert sorted([dataclasses.replace(p, schema=None) for p in schema_params], key=lambda p: p.name) == [  # type: ignore[union-attr]
        OpenAPIParameter(name="cookie_param", param_in=ParamType.COOKIE, required=True),
        OpenAPIParameter(name="header_param", param_in=ParamType.HEADER, required=True),
        OpenAPIParameter(name="path_param", param_in=ParamType.PATH, required=True),
        OpenAPIParameter(name="query_param", param_in=ParamType.QUERY, required=True),
    ]

    with TestClient(app, raise_server_exceptions=True) as client:
        client.cookies.set("cookie_param", "4")
        res = client.get("/1?query_param=2", headers={"header_param": "3"})
        assert res.status_code == 200
        assert res.json() == {"path": 1, "query": 2, "header": 3, "cookie": 4}


def test_simple_form_dependency() -> None:
    async def dependency(
        path_param: FromPath[int],
        query_param: FromQuery[int],
        header_param: FromHeader[int],
        cookie_param: FromCookie[int],
    ) -> Dict[str, int]:
        return {"query": query_param, "header": header_param, "cookie": cookie_param, "path": path_param}

    @get("/{path_param:int}", dependencies={"dep": dependency})
    def handler(dep: Dict[str, int]) -> Dict[str, int]:
        return dep

    with create_test_client([handler], raise_server_exceptions=True) as client:
        client.cookies.set("cookie_param", "4")
        res = client.get("/1?query_param=2", headers={"header_param": "3"})
        assert res.status_code == 200
        assert res.json() == {"path": 1, "query": 2, "header": 3, "cookie": 4}


def test_explicit_form_dependency() -> None:
    async def dependency(
        path_param: Annotated[int, PathParameter()],
        query_param: Annotated[int, QueryParameter()],
        header_param: Annotated[int, HeaderParameter()],
        cookie_param: Annotated[int, CookieParameter()],
    ) -> Dict[str, int]:
        return {"query": query_param, "header": header_param, "cookie": cookie_param, "path": path_param}

    @get("/{path_param:int}", dependencies={"dep": dependency})
    def handler(dep: Dict[str, int]) -> Dict[str, int]:
        return dep

    with create_test_client([handler], raise_server_exceptions=True) as client:
        client.cookies.set("cookie_param", "4")
        res = client.get("/1?query_param=2", headers={"header_param": "3"})
        assert res.status_code == 200
        assert res.json() == {"path": 1, "query": 2, "header": 3, "cookie": 4}


def test_explicit_form_with_alias_dependency() -> None:
    async def dependency(
        path_p: Annotated[int, PathParameter(name="path_param")],
        query_p: Annotated[int, QueryParameter(name="query_param")],
        header_p: Annotated[int, HeaderParameter(name="header_param")],
        cookie_p: Annotated[int, CookieParameter(name="cookie_param")],
    ) -> Dict[str, int]:
        return {"query": query_p, "header": header_p, "cookie": cookie_p, "path": path_p}

    @get("/{path_param:int}", dependencies={"dep": dependency})
    def handler(dep: Dict[str, int]) -> Dict[str, int]:
        return dep

    app = Litestar([handler])
    schema_params = app.openapi_schema.paths["/{path_param}"].get.parameters  # type: ignore[index, union-attr]

    assert sorted([dataclasses.replace(p, schema=None) for p in schema_params], key=lambda p: p.name) == [  # type: ignore[union-attr]
        OpenAPIParameter(name="cookie_param", param_in=ParamType.COOKIE, required=True),
        OpenAPIParameter(name="header_param", param_in=ParamType.HEADER, required=True),
        OpenAPIParameter(name="path_param", param_in=ParamType.PATH, required=True),
        OpenAPIParameter(name="query_param", param_in=ParamType.QUERY, required=True),
    ]

    with TestClient(app, raise_server_exceptions=True) as client:
        client.cookies.set("cookie_param", "4")
        res = client.get("/1?query_param=2", headers={"header_param": "3"})
        assert res.status_code == 200
        assert res.json() == {"path": 1, "query": 2, "header": 3, "cookie": 4}


@pytest.mark.parametrize(
    "default,type_",
    [
        (_legacy_parameter(query="query"), "query"),
        (_legacy_parameter(header="header"), "header"),
        (_legacy_parameter(cookie="cookie"), "cookie"),
    ],
)
def test_deprecated_default_style_handler(default: ParameterKwarg, type_: str) -> None:
    @get("/")
    def handler(some_param: str = default) -> None:  # type: ignore[assignment]
        pass

    with pytest.warns(
        LitestarDeprecationWarning,
        match=f"{type_} parameter 'some_param' declared using deprecated default 'param: <type>",
    ):
        Litestar([handler])


@pytest.mark.parametrize(
    "default,type_",
    [
        (_legacy_parameter(query="query"), "query"),
        (_legacy_parameter(header="header"), "header"),
        (_legacy_parameter(cookie="cookie"), "cookie"),
    ],
)
def test_deprecated_default_style_dependency(default: ParameterKwarg, type_: str) -> None:
    def dependency(some_param: str = default) -> None:  # type: ignore[assignment]
        pass

    @get("/", dependencies={"some_dependency": dependency})
    def handler(some_dependency: None) -> None:
        pass

    with pytest.warns(
        LitestarDeprecationWarning,
        match=f"{type_} parameter 'some_param' declared using deprecated default 'param: <type>",
    ):
        Litestar([handler])


@pytest.mark.parametrize(
    "annotation,type_",
    [
        (Annotated[str, _legacy_parameter(query="query")], "query"),
        (Annotated[str, _legacy_parameter(header="header")], "header"),
        (Annotated[str, _legacy_parameter(cookie="cookie")], "cookie"),
    ],
)
def test_deprecated_annotated_style_handler(annotation: Any, type_: str) -> None:
    @get("/")
    def handler(some_param: annotation) -> None:
        pass

    with pytest.warns(
        LitestarDeprecationWarning,
        match=f"{type_} parameter 'some_param' declared using deprecated annotated 'param: Annotated",
    ):
        Litestar([handler])


@pytest.mark.parametrize(
    "annotation,type_",
    [
        (Annotated[str, _legacy_parameter(query="query")], "query"),
        (Annotated[str, _legacy_parameter(header="header")], "header"),
        (Annotated[str, _legacy_parameter(cookie="cookie")], "cookie"),
    ],
)
def test_deprecated_annotated_style_dependency(annotation: Any, type_: str) -> None:
    def dependency(some_param: annotation) -> None:
        pass

    @get("/", dependencies={"some_dependency": dependency})
    def handler(some_dependency: None) -> None:
        return None

    with pytest.warns(
        LitestarDeprecationWarning,
        match=f"{type_} parameter 'some_param' declared using deprecated annotated 'param: Annotated",
    ):
        Litestar([handler])


def test_deprecated_implicit_style_handler() -> None:
    @get("/query")
    def query_handler(query_param: str) -> None:
        pass

    @get("/{path_param:str}")
    def path_handler(path_param: str) -> None:
        pass

    with pytest.warns(
        LitestarDeprecationWarning, match="query parameter 'query_param' declared using deprecated inferred"
    ):
        Litestar([query_handler])

    with pytest.warns(
        LitestarDeprecationWarning, match="path parameter 'path_param' declared using deprecated inferred"
    ):
        Litestar([path_handler])


def test_deprecated_implicit_style_dependency() -> None:
    def query_dependency(query_param: str) -> None:
        pass

    def path_dependency(path_param: str) -> None:
        pass

    @get("/query", dependencies={"query_d": query_dependency})
    def query_handler(query_d: None) -> None:
        pass

    @get("/{path_param:str}", dependencies={"path_d": path_dependency})
    def path_handler(path_d: None) -> None:
        pass

    with pytest.warns(
        LitestarDeprecationWarning, match="query parameter 'query_param' declared using deprecated inferred"
    ):
        Litestar([query_handler])

    with pytest.warns(
        LitestarDeprecationWarning, match="path parameter 'path_param' declared using deprecated inferred"
    ):
        Litestar([path_handler])


def test_annotated_metadata_does_not_shadow_dependency() -> None:
    # https://github.com/litestar-org/litestar/issues/4804
    async def provide_foo() -> str:
        return "from-dependency"

    @get("/", dependencies={"foo": provide_foo})
    async def handler(foo: Annotated[str, "arbitrary metadata"]) -> str:
        return foo

    with create_test_client([handler]) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert res.text == "from-dependency"


def test_constraint_metadata_does_not_shadow_dependency() -> None:
    # https://github.com/litestar-org/litestar/issues/4804

    async def provide_foo() -> int:
        return 42

    @get("/", dependencies={"foo": provide_foo})
    async def handler(foo: Annotated[int, annotated_types.Gt(5)]) -> int:
        return foo

    with create_test_client([handler]) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert res.json() == 42


def test_annotated_metadata_does_not_shadow_path_param() -> None:
    # https://github.com/litestar-org/litestar/issues/4804

    @get("/{foo:int}")
    async def handler(foo: Annotated[int, "arbitrary metadata"]) -> int:
        return foo

    with create_test_client([handler]) as client:
        res = client.get("/7")
        assert res.status_code == 200
        assert res.json() == 7


@pytest.mark.filterwarnings(
    "ignore:.*Dependency parameter 'foo' declared using deprecated:litestar.exceptions.LitestarDeprecationWarning"
)
def test_deprecated_dependency_marker() -> None:
    with pytest.warns(LitestarDeprecationWarning, match="Call to deprecated function 'Dependency'"):

        @get("/")
        async def handler(foo: Annotated[int, Dependency()] = 1) -> None:
            pass

        Litestar([handler])


def test_named_dependency_explicit_marker() -> None:

    @get("/")
    async def handler(foo: NamedDependency[int] = 1) -> int:
        return foo

    with create_test_client([handler]) as client:
        # uses parameter default
        assert client.get("/").json() == 1

        # isn't implicitly treated as a query parameter
        schema = client.get("/schema/openapi.json").json()
        assert schema["paths"]["/"]["get"].get("parameters") is None
