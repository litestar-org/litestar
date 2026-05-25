from typing import Any, Dict, Generator, List, Optional

import pytest
from typing_extensions import Annotated

from litestar import Controller, Litestar, MediaType, get, post
from litestar.di import NamedDependency, Provide
from litestar.exceptions import ImproperlyConfiguredException, LitestarDeprecationWarning
from litestar.params import Body, Dependency, FromQuery, Parameter, QueryParameter, SkipValidation
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR
from litestar.testing import TestClient, create_test_client

pytestmark = pytest.mark.filterwarnings("ignore::litestar.exceptions.LitestarDeprecationWarning")


def test_parsing_of_parameter_as_annotated() -> None:
    @get(path="/")
    def handler(param: Annotated[str, QueryParameter(min_length=1)]) -> str:
        return param

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.status_code == HTTP_400_BAD_REQUEST

        response = client.get("/?param=a")
        assert response.status_code == HTTP_200_OK


def test_parsing_of_parameter_as_default() -> None:
    @get(path="/")
    def handler(param: str = Parameter(min_length=1)) -> str:
        return param

    with create_test_client(handler) as client:
        response = client.get("/?param=")
        assert response.status_code == HTTP_400_BAD_REQUEST

        response = client.get("/?param=a")
        assert response.status_code == HTTP_200_OK


def test_parsing_of_body_as_annotated() -> None:
    @post(path="/")
    def handler(data: Annotated[List[str], Body(min_items=1)]) -> List[str]:
        return data

    with create_test_client(handler) as client:
        response = client.post("/", json=[])
        assert response.status_code == HTTP_400_BAD_REQUEST

        response = client.post("/", json=["a"])
        assert response.status_code == HTTP_201_CREATED


def test_parsing_of_body_as_default() -> None:
    @post(path="/")
    def handler(data: List[str] = Body(min_items=1)) -> List[str]:
        return data

    with create_test_client(handler) as client:
        response = client.post("/", json=[])
        assert response.status_code == HTTP_400_BAD_REQUEST

        response = client.post("/", json=["a"])
        assert response.status_code == HTTP_201_CREATED


def test_parsing_of_dependency_as_annotated_deprecated() -> None:
    @get(path="/", dependencies={"dep": Provide(lambda: None, sync_to_thread=False)})
    def handler(dep: Annotated[None, Dependency()]) -> None:
        return dep

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.text == "null"


def test_parsing_of_dependency_as_annotated() -> None:
    @get(path="/", dependencies={"dep": Provide(lambda: None, sync_to_thread=False)})
    def handler(dep: NamedDependency[None]) -> None:
        return dep

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.text == "null"


def test_parsing_of_dependency_as_default() -> None:
    @get(path="/", dependencies={"dep": Provide(lambda: None, sync_to_thread=False)})
    def handler(dep: None = Dependency()) -> None:
        return dep

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.text == "null"


@pytest.mark.parametrize(
    "dependency_default, expected",
    [
        (..., None),
        (None, None),
        (13, 13),
    ],
)
def test_dependency_defaults_deprecated(dependency_default: Any, expected: Optional[int]) -> None:
    with pytest.warns(LitestarDeprecationWarning):
        dependency = Dependency(default=dependency_default) if dependency_default is not ... else Dependency()

    @get("/")
    def handler(value: Optional[int] = dependency) -> Dict[str, Optional[int]]:
        return {"value": value}

    with create_test_client(route_handlers=[handler]) as client:
        resp = client.get("/")
        assert resp.json() == {"value": expected}


@pytest.mark.parametrize(
    "dependency_default, expected",
    [
        (..., None),
        (None, None),
        (13, 13),
    ],
)
def test_dependency_defaults(dependency_default: Any, expected: Optional[int]) -> None:
    @get("/")
    def handler(value: Optional[int] = dependency_default) -> Dict[str, Optional[int]]:
        return {"value": value}

    with create_test_client(route_handlers=[handler]) as client:
        resp = client.get("/")
        assert resp.json() == {"value": expected}


def test_dependency_non_optional_with_default_deprecated() -> None:
    @get("/")
    def handler(value: int = Dependency(default=13)) -> Dict[str, int]:
        return {"value": value}

    with create_test_client(route_handlers=[handler]) as client:
        resp = client.get("/")
        assert resp.json() == {"value": 13}


def test_dependency_non_optional_with_default() -> None:
    @get("/")
    def handler(value: int = 13) -> Dict[str, int]:
        return {"value": value}

    with create_test_client(route_handlers=[handler]) as client:
        resp = client.get("/")
        assert resp.json() == {"value": 13}


def test_dependency_no_default_deprecated() -> None:
    @get(dependencies={"value": Provide(lambda: 13, sync_to_thread=False)})
    def test(value: int = Dependency()) -> Dict[str, int]:
        return {"value": value}

    with create_test_client(route_handlers=[test]) as client:
        resp = client.get("/")
    assert resp.json() == {"value": 13}


def test_dependency_no_default() -> None:
    @get(dependencies={"value": Provide(lambda: 13, sync_to_thread=False)})
    def test(value: int) -> Dict[str, int]:
        return {"value": value}

    with create_test_client(route_handlers=[test]) as client:
        resp = client.get("/")
    assert resp.json() == {"value": 13}


def test_dependency_not_provided_and_no_default() -> None:
    @get()
    def test(value: NamedDependency[int]) -> Dict[str, int]:
        return {"value": value}

    with pytest.raises(ImproperlyConfiguredException):
        Litestar(route_handlers=[test])


def test_dependency_provided_on_controller() -> None:
    """Ensures that we don't only consider the handler's dependencies when checking that an explicit non-optional
    dependency has been provided.
    """

    class C(Controller):
        path = ""
        dependencies = {"value": Provide(lambda: 13, sync_to_thread=False)}

        @get()
        def test(self, value: int) -> Dict[str, int]:
            return {"value": value}

    with create_test_client(route_handlers=[C]) as client:
        resp = client.get("/")
    assert resp.json() == {"value": 13}


def test_dependency_skip_validation() -> None:
    @get("/validated")
    def validated(value: int = Dependency()) -> Dict[str, int]:
        return {"value": value}

    @get("/skipped")
    def skipped(value: SkipValidation[int]) -> Dict[str, int]:
        return {"value": value}

    with create_test_client(
        route_handlers=[validated, skipped], dependencies={"value": Provide(lambda: "str", sync_to_thread=False)}
    ) as client:
        validated_resp = client.get("/validated")
        assert validated_resp.status_code == HTTP_500_INTERNAL_SERVER_ERROR
        skipped_resp = client.get("/skipped")
        assert skipped_resp.status_code == HTTP_200_OK
        assert skipped_resp.json() == {"value": "str"}


def test_dependency_skip_validation_with_default() -> None:
    @get("/skipped")
    def skipped(value: SkipValidation[int] = 1) -> Dict[str, int]:
        return {"value": value}

    with create_test_client(route_handlers=[skipped]) as client:
        skipped_resp = client.get("/skipped")
        assert skipped_resp.status_code == HTTP_200_OK
        assert skipped_resp.json() == {"value": 1}


def test_dependency_default_is_not_treated_as_query_parameter() -> None:
    @get("/")
    def handler(value: int = Dependency(default=42)) -> Dict[str, int]:
        return {"value": value}

    with create_test_client(route_handlers=[handler]) as client:
        schema_resp = client.get("/schema/openapi.json")
        assert schema_resp.status_code == HTTP_200_OK
        operation = schema_resp.json()["paths"]["/"]["get"]
        # the dependency must not appear as any kind of HTTP parameter
        assert "parameters" not in operation


def test_dependency_default_does_not_collide_with_query_param_of_same_name() -> None:
    """A query parameter on a handler can share a name with a dependency-with-default
    declared on a downstream provider, without the dependency's default leaking into
    the handler's query parameter.
    """

    def provide_value(value: int = Dependency(default=7)) -> int:
        return value * 10

    @get("/", dependencies={"computed": Provide(provide_value, sync_to_thread=False)})
    def handler(computed: int) -> Dict[str, int]:
        return {"computed": computed}

    with create_test_client(route_handlers=[handler]) as client:
        resp = client.get("/")
        assert resp.status_code == HTTP_200_OK
        assert resp.json() == {"computed": 70}


def test_dependency_nested_sequence() -> None:
    class Obj:
        def __init__(self, seq: List[str]) -> None:
            self.seq = seq

    async def provides_obj(seq: FromQuery[List[str]]) -> Obj:
        return Obj(seq)

    @get("/obj")
    def get_obj(obj: Obj) -> List[str]:
        return obj.seq

    @get("/seq")
    def get_seq(seq: FromQuery[List[str]]) -> List[str]:
        return seq

    with create_test_client(
        route_handlers=[get_obj, get_seq],
        dependencies={"obj": Provide(provides_obj)},
    ) as client:
        seq = ["a", "b", "c"]
        resp = client.get("/seq", params={"seq": seq})
        assert resp.json() == ["a", "b", "c"]
        resp = client.get("/obj", params={"seq": seq})
        assert resp.json() == ["a", "b", "c"]


def test_regex_validation() -> None:
    # https://github.com/litestar-org/litestar/issues/1860
    @get(path="/val_regex", media_type=MediaType.TEXT)
    async def regex_val(text: Annotated[str, QueryParameter(title="a or b", pattern="[a|b]")]) -> str:
        return f"str: {text}"

    with create_test_client(route_handlers=[regex_val]) as client:
        for letter in ("a", "b"):
            response = client.get(f"/val_regex?text={letter}")
            assert response.status_code == HTTP_200_OK
            assert response.text == f"str: {letter}"

        response = client.get("/val_regex?text=c")
        assert response.status_code == HTTP_400_BAD_REQUEST


@pytest.fixture(name="optional_no_default_client")
def optional_no_default_client_fixture() -> Generator[TestClient, None, None]:
    @get("/optional-no-default")
    def handle_optional(key: FromQuery[Optional[str]]) -> Dict[str, Optional[str]]:
        return {"key": key}

    @get("/optional-annotated-no-default")
    def handle_optional_annotated(
        param: Annotated[Optional[str], QueryParameter(name="key")],
    ) -> Dict[str, Optional[str]]:
        return {"key": param}

    with create_test_client(route_handlers=[handle_optional, handle_optional_annotated], openapi_config=None) as client:
        yield client


def test_optional_query_parameter_consistency_no_default_queried_without_param(
    optional_no_default_client: TestClient,
) -> None:
    assert optional_no_default_client.get("/optional-no-default", params={}).json() == {"key": None}
    assert optional_no_default_client.get("/optional-annotated-no-default", params={}).json() == {"key": None}


def test_optional_query_parameter_consistency_no_default_queried_with_expected_param(
    optional_no_default_client: TestClient,
) -> None:
    assert optional_no_default_client.get("/optional-no-default", params={"key": "a"}).json() == {"key": "a"}
    assert optional_no_default_client.get("/optional-annotated-no-default", params={"key": "a"}).json() == {"key": "a"}


def test_optional_query_parameter_consistency_no_default_queried_with_other_param(
    optional_no_default_client: TestClient,
) -> None:
    assert optional_no_default_client.get("/optional-no-default", params={"param": "a"}).json() == {"key": None}
    assert optional_no_default_client.get("/optional-annotated-no-default", params={"param": "a"}).json() == {
        "key": None
    }


@pytest.fixture(name="optional_default_client")
def optional_default_client_fixture() -> Generator[TestClient, None, None]:
    @get("/optional-default")
    def handle_default(key: FromQuery[Optional[str]] = None) -> Dict[str, Optional[str]]:
        return {"key": key}

    @get("/optional-annotated-default")
    def handle_default_annotated(
        param: Annotated[Optional[str], QueryParameter(name="key")] = None,
    ) -> Dict[str, Optional[str]]:
        return {"key": param}

    with create_test_client(route_handlers=[handle_default, handle_default_annotated], openapi_config=None) as client:
        yield client


def test_optional_query_parameter_consistency_with_default_queried_without_param(
    optional_default_client: TestClient,
) -> None:
    assert optional_default_client.get("/optional-default", params={}).json() == {"key": None}
    assert optional_default_client.get("/optional-annotated-default", params={}).json() == {"key": None}


def test_optional_query_parameter_consistency_with_default_queried_with_expected_param(
    optional_default_client: TestClient,
) -> None:
    assert optional_default_client.get("/optional-default", params={"key": "a"}).json() == {"key": "a"}
    assert optional_default_client.get("/optional-annotated-default", params={"key": "a"}).json() == {"key": "a"}


def test_optional_query_parameter_consistency_with_default_queried_with_other_param(
    optional_default_client: TestClient,
) -> None:
    assert optional_default_client.get("/optional-default", params={"param": "a"}).json() == {"key": None}
    assert optional_default_client.get("/optional-annotated-default", params={"abc": "xyz"}).json() == {"key": None}
    assert optional_default_client.get("/optional-annotated-default", params={"param": "a"}).json() == {"key": None}


def test_not_included_in_schema_param_as_annotated() -> None:
    @get(path="/")
    def handler(param: Annotated[str, QueryParameter(include_in_schema=True)]) -> str:
        return param

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.status_code == HTTP_400_BAD_REQUEST

        response = client.get("/?param=a")
        assert response.status_code == HTTP_200_OK
        assert response.text == "a"


def test_not_included_in_schema_param_as_default() -> None:
    @get(path="/")
    def handler(param: Annotated[str, QueryParameter(include_in_schema=True)]) -> str:
        return param

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.status_code == HTTP_400_BAD_REQUEST

        response = client.get("/?param=a")
        assert response.status_code == HTTP_200_OK
        assert response.text == "a"


def test_not_included_in_schema_param_with_default_value() -> None:
    @get(path="/")
    def handler(param: Annotated[str, QueryParameter(include_in_schema=True)] = "b") -> str:
        return param

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.text == "b"
