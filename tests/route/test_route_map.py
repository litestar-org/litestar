import re
from random import shuffle
from string import ascii_letters
from typing import Any, Dict, List, Set, Tuple, cast

from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.strategies import DrawFn

from starlite import HTTPRoute, get
from starlite.middleware import ExceptionHandlerMiddleware
from starlite.testing import create_test_client

param_pat = re.compile(r"{.*?:int}")

RouteMapTestCase = Tuple[str, str, Set[str]]


def is_path_in_route_map(route_map: Dict[str, Any], path: str, path_params: Set[str]) -> bool:
    if not path_params:
        return path in route_map
    components = ["/", *[component for component in param_pat.sub("*", path).split("/") if component]]
    cur_node = route_map
    for component in components:
        if component not in cur_node:
            return False
        cur_node = cur_node[component]
    route_params = {param["full"] for param in cur_node.get("_path_parameters", [])}
    if path_params == route_params:
        return True
    return False


@st.composite
def route_test_paths(draw: DrawFn) -> List[RouteMapTestCase]:
    def build_record(components: List[str], params: Set[str]) -> RouteMapTestCase:
        segments = components + [f"{{{p}:int}}" for p in params]
        shuffle(segments)
        router_path = "/" + "/".join(segments)
        request_path = param_pat.sub("1", router_path)
        return (router_path, request_path, {f"{p}:int" for p in params})

    parameter_names = ["a", "b", "c", "d", "e"]
    param_st = st.sets(st.sampled_from(parameter_names), min_size=0, max_size=3)
    components_st = st.lists(st.text(alphabet=ascii_letters, min_size=1, max_size=4), min_size=1, max_size=3)
    path_st = st.builds(build_record, components_st, param_st)
    return cast(
        List[RouteMapTestCase], draw(st.lists(path_st, min_size=10, max_size=10, unique_by=lambda record: record[1]))
    )


def test_route_map_starts_empty() -> None:
    @get(path=[])
    def handler_fn() -> None:
        ...

    client = create_test_client(handler_fn)
    route_map = client.app.route_map
    assert route_map["_components"] == set()
    assert list(route_map.keys()) == ["_components", "/"]


@given(test_paths=route_test_paths())
@settings(
    max_examples=5,
    deadline=None,
)
def test_add_route_map_path(test_paths: List[RouteMapTestCase]) -> None:
    @get(path=[])
    def handler_fn(a: int = 0, b: int = 0, c: int = 0, d: int = 0, e: int = 0) -> None:
        ...

    client = create_test_client(handler_fn)
    app = client.app
    route_map = app.route_map
    for router_path, _, path_params in test_paths:
        assert is_path_in_route_map(route_map, router_path, path_params) is False
        route = HTTPRoute(
            path=router_path,
            route_handlers=[get(path=router_path)(handler_fn)],
        )
        app.add_node_to_route_map(route)
        assert is_path_in_route_map(route_map, router_path, path_params) is True


@given(test_paths=route_test_paths())
@settings(
    max_examples=5,
    deadline=None,
)
def test_handler_paths_added(test_paths: List[RouteMapTestCase]) -> None:
    @get(path=[router_path for router_path, _, _ in test_paths])
    def handler_fn(a: int = 0, b: int = 0, c: int = 0, d: int = 0, e: int = 0) -> None:
        ...

    client = create_test_client(handler_fn)
    route_map = client.app.route_map
    for router_path, _, path_params in test_paths:
        assert is_path_in_route_map(route_map, router_path, path_params) is True


@given(test_paths=route_test_paths())
@settings(
    max_examples=5,
    deadline=None,
)
def test_find_existing_asgi_handlers(test_paths: List[RouteMapTestCase]) -> None:
    def handler_fn(a: int = 0, b: int = 0) -> None:
        ...

    client = create_test_client(get(path=[router_path for router_path, _, _ in test_paths])(handler_fn))
    app = client.app
    router = app.asgi_router
    for router_path, request_path, _ in test_paths:
        route = HTTPRoute(
            path=router_path,
            route_handlers=[get(path=router_path)(handler_fn)],
        )
        app.add_node_to_route_map(route)
        asgi_handlers, is_asgi = router.parse_scope_to_route({"path": request_path})
        assert "GET" in asgi_handlers and isinstance(asgi_handlers["GET"], ExceptionHandlerMiddleware)
        assert is_asgi is False


@given(test_paths=route_test_paths())
@settings(
    max_examples=5,
    deadline=None,
)
def test_missing_asgi_handlers(test_paths: List[RouteMapTestCase]) -> None:
    def handler_fn(a: int = 0, b: int = 0) -> None:
        ...

    client = create_test_client(get(path=[])(handler_fn))
    app = client.app
    router = app.asgi_router
    for router_path, request_path, _ in test_paths:
        route = HTTPRoute(
            path=router_path,
            route_handlers=[get(path=router_path)(handler_fn)],
        )
        app.add_node_to_route_map(route)
        assert router.parse_scope_to_route({"path": request_path}) == ({}, False)
