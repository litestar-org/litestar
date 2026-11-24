from dataclasses import dataclass
from typing import Annotated, Any

import pytest

from litestar import Litestar, Router, get, post
from litestar.di import NamedDependency, Provide, Provider
from litestar.params import FromHeader, FromPath, FromQuery, HeaderParameter, JSONBody, QueryParameter
from litestar.testing import TestClient


def test_header_read_case_insensitively() -> None:
    @get("/")
    async def handler(token: Annotated[str, HeaderParameter(name="X-Token")]) -> str:
        return token

    with TestClient(Litestar([handler], openapi_config=None)) as client:
        assert client.get("/", headers={"x-TOKEN": "t"}).text == "t"


def test_missing_and_invalid_parameters_reported_together() -> None:
    @get("/")
    async def handler(
        page_size: Annotated[int, QueryParameter(name="page-size")], database: FromQuery[int], token: FromHeader[str]
    ) -> None: ...

    with TestClient(Litestar([handler], openapi_config=None)) as client:
        response = client.get("/?database=x")

    assert response.status_code == 400
    assert response.json()["detail"] == "Validation failed for GET /?database=x"
    assert response.json()["extra"] == [
        {"message": "Missing required query parameter", "key": "page-size", "source": "query"},
        {"message": "Expected `int`, got `str`", "key": "database", "source": "query"},
        {"message": "Missing required header parameter", "key": "token", "source": "header"},
    ]


def test_type_decoders_apply_to_request_parameters_of_handler_and_dependency() -> None:
    class Token:
        def __init__(self, value: str) -> None:
            self.value = value

    async def provide_length(token: FromQuery[Token]) -> int:
        return len(token.value)

    @get(
        "/",
        dependencies={"length": Provide(provide_length)},
        type_decoders=[(lambda t: t is Token, lambda t, v: t(v))],
    )
    async def handler(token: FromQuery[Token], length: NamedDependency[int]) -> dict:
        return {"token": token.value, "length": length}

    with TestClient(Litestar([handler], openapi_config=None)) as client:
        assert client.get("/?token=abc").json() == {"token": "abc", "length": 3}


def test_type_decoders_of_two_handlers_for_one_type() -> None:
    class Token:
        def __init__(self, value: str) -> None:
            self.value = value

    @get("/upper", type_decoders=[(lambda t: t is Token, lambda t, v: t(v.upper()))])
    async def upper(token: FromQuery[Token]) -> str:
        return token.value

    @get("/lower", type_decoders=[(lambda t: t is Token, lambda t, v: t(v.lower()))])
    async def lower(token: FromQuery[Token]) -> str:
        return token.value

    with TestClient(Litestar([upper, lower], openapi_config=None)) as client:
        assert client.get("/upper?token=aBc").text == "ABC"
        assert client.get("/lower?token=aBc").text == "abc"


def test_type_decoder_of_other_handler_not_applied() -> None:
    class Token:
        def __init__(self, value: str) -> None:
            self.value = value

    @get("/with", type_decoders=[(lambda t: t is Token, lambda t, v: t(v))])
    async def with_decoder(token: FromQuery[Token]) -> str:
        return token.value

    @get("/without")
    async def without_decoder(token: FromQuery[Token]) -> str:
        return token.value

    with TestClient(Litestar([with_decoder, without_decoder], openapi_config=None)) as client:
        assert client.get("/with?token=abc").text == "abc"
        assert client.get("/without?token=abc").status_code == 400


@pytest.mark.parametrize(
    "query", ["?token=abc&page=1", "?token=abc&page=x", "?token=abc"], ids=["valid", "invalid", "missing"]
)
def test_type_decoder_raising_other_than_validation_error_is_server_error(query: str) -> None:
    class Token:
        pass

    def decode(type_: Any, value: Any) -> Any:
        raise RuntimeError("decoder broke")

    @get("/", type_decoders=[(lambda t: t is Token, decode)])
    async def handler(token: FromQuery[Token], page: FromQuery[int]) -> None: ...

    with TestClient(Litestar([handler], openapi_config=None), raise_server_exceptions=False) as client:
        assert client.get(f"/{query}").status_code == 500


def test_parameter_declared_by_handler_and_dependency_is_one_parameter() -> None:
    async def provide_double(size: Annotated[int, QueryParameter(name="page-size")]) -> int:
        return size * 2

    @get("/", dependencies={"double": Provide(provide_double)})
    async def handler(
        page_size: Annotated[int, QueryParameter(name="page-size")], double: NamedDependency[int]
    ) -> dict:
        return {"page_size": page_size, "double": double}

    with TestClient(Litestar([handler], openapi_config=None)) as client:
        assert client.get("/?page-size=5").json() == {"page_size": 5, "double": 10}


def test_header_declared_in_different_cases_is_one_parameter() -> None:
    async def provide_token(token: Annotated[str, HeaderParameter(name="x-token")]) -> str:
        return token

    @get("/", dependencies={"provided": Provide(provide_token)})
    async def handler(token: Annotated[str, HeaderParameter(name="X-Token")], provided: NamedDependency[str]) -> dict:
        return {"token": token, "provided": provided}

    with TestClient(Litestar([handler], openapi_config=None)) as client:
        assert client.get("/", headers={"X-TOKEN": "t"}).json() == {"token": "t", "provided": "t"}


def test_layer_parameter_without_annotation_takes_type_of_handler_and_keeps_constraint() -> None:
    @get("/")
    async def handler(limit: FromQuery[int]) -> dict:
        return {"limit": limit}

    router = Router("/", route_handlers=[handler], parameters={"limit": QueryParameter(gt=0)})
    with TestClient(Litestar([router], openapi_config=None)) as client:
        assert client.get("/?limit=5").json() == {"limit": 5}
        wrong_type = client.get("/?limit=x")
        violated = client.get("/?limit=0")

    assert wrong_type.json()["extra"] == [{"message": "Expected `int`, got `str`", "key": "limit", "source": "query"}]
    assert violated.json()["extra"] == [{"message": "Expected `int` >= 1", "key": "limit", "source": "query"}]


def test_documentation_only_layer_parameter_constraint_not_applied() -> None:
    @get("/")
    async def handler() -> None: ...

    layer_parameters = {"limit": QueryParameter(annotation=int, gt=3, documentation_only=True)}
    with TestClient(Litestar([handler], parameters=layer_parameters, openapi_config=None)) as client:
        assert client.get("/?limit=2").status_code == 200


def test_documentation_only_layer_parameter_bound_by_handler_constraint_not_applied() -> None:
    @get("/")
    async def handler(limit: FromQuery[int]) -> int:
        return limit

    router = Router("/", route_handlers=[handler], parameters={"limit": QueryParameter(gt=3, documentation_only=True)})
    with TestClient(Litestar([router], openapi_config=None)) as client:
        assert client.get("/?limit=2").json() == 2
        wrong_type = client.get("/?limit=x")

    assert wrong_type.json()["extra"] == [{"message": "Expected `int`, got `str`", "key": "limit", "source": "query"}]


def test_documentation_only_handler_parameter_constraint_not_applied() -> None:
    @get("/")
    async def handler(limit: Annotated[int, QueryParameter(gt=3, documentation_only=True)]) -> int:
        return limit

    with TestClient(Litestar([handler], openapi_config=None)) as client:
        assert client.get("/?limit=2").json() == 2


def test_only_bare_marker_of_layer_parameter_type_binds_it() -> None:
    @get("/")
    async def handler(limit: FromQuery[int], header: FromHeader[str]) -> dict:
        return {"limit": limit, "header": header}

    layer_parameters = {"limit": QueryParameter(annotation=int, gt=0), "header": QueryParameter(annotation=str)}
    with TestClient(Litestar([handler], parameters=layer_parameters, openapi_config=None)) as client:
        complete = client.get("/?limit=1&header=q", headers={"header": "h"})
        without_query_header = client.get("/?limit=1", headers={"header": "h"})
        limit_violated = client.get("/?limit=0&header=q", headers={"header": "h"})

    assert complete.json() == {"limit": 1, "header": "h"}
    assert without_query_header.json()["extra"] == [
        {"message": "Missing required query parameter", "key": "header", "source": "query"}
    ]
    assert limit_violated.json()["extra"] == [{"message": "Expected `int` >= 1", "key": "limit", "source": "query"}]


def test_provider_bare_marker_merged_with_layer_parameter() -> None:
    async def provide_limit(limit: FromQuery[int]) -> int:
        return limit

    @get("/", dependencies={"provided": Provide(provide_limit)})
    async def handler(provided: NamedDependency[int]) -> int:
        return provided

    layer_parameters = {"limit": QueryParameter(annotation=int, name="page-limit", gt=0)}
    with TestClient(Litestar([handler], parameters=layer_parameters, openapi_config=None)) as client:
        assert client.get("/?page-limit=5").json() == 5
        violated = client.get("/?page-limit=0")

    assert violated.json()["extra"] == [{"message": "Expected `int` >= 1", "key": "page-limit", "source": "query"}]


def test_shared_provider_merged_with_layer_parameter_per_handler() -> None:
    async def provide_limit(limit: FromQuery[int]) -> int:
        return limit

    @get("/")
    async def handler(provided: NamedDependency[int]) -> int:
        return provided

    renamed = Router("/renamed", route_handlers=[handler], parameters={"limit": QueryParameter(name="page-limit")})
    plain = Router("/plain", route_handlers=[handler])
    app = Litestar([renamed, plain], dependencies=[Provider(provide_limit, key="provided")], openapi_config=None)
    with TestClient(app) as client:
        assert client.get("/renamed?page-limit=5").json() == 5
        assert client.get("/plain?limit=3").json() == 3


def test_path_parameter_with_default_on_paths_with_and_without_segment() -> None:
    async def provide_user_id(user_id: FromPath[int] = 0) -> int:
        return user_id

    @get(["/", "/{user_id:int}"], dependencies={"provided": Provide(provide_user_id)})
    async def handler(provided: NamedDependency[int]) -> dict:
        return {"user_id": provided}

    with TestClient(Litestar([handler], openapi_config=None)) as client:
        assert client.get("/").json() == {"user_id": 0}
        assert client.get("/5").json() == {"user_id": 5}


@dataclass
class Person:
    name: str
    age: int


def test_missing_and_invalid_body_reported() -> None:
    @post("/")
    async def handler(data: JSONBody[Person]) -> Person:
        return data

    with TestClient(Litestar([handler], openapi_config=None)) as client:
        missing = client.post("/")
        invalid = client.post("/", json={"name": "a", "age": "x"})

    assert missing.status_code == 400
    assert missing.json()["extra"] == [{"message": "Missing required request body", "key": "data", "source": "body"}]
    assert invalid.status_code == 400
    assert invalid.json()["extra"] == [{"message": "Expected `int`, got `str`", "key": "age", "source": "body"}]
