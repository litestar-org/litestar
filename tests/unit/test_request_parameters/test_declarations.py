# pyright: reportUnnecessaryTypeIgnoreComment=false
from dataclasses import dataclass
from typing import Annotated, Any

import pytest

from litestar import Litestar, get, post
from litestar.di import NamedDependency, Provide
from litestar.exceptions import ImproperlyConfiguredException
from litestar.params import FromPath, FromQuery, JSONBody, MsgPackBody, QueryParameter


@dataclass
class Person:
    name: str


@pytest.mark.parametrize(
    ("provider_annotation", "provider_default", "message"),
    [
        pytest.param(FromQuery[str], 5, "type 'int' and type 'str'", id="type"),
        pytest.param(FromQuery[int], 10, "default 5 and default 10", id="default"),
        pytest.param(Annotated[int, QueryParameter(gt=0)], 5, "gt None and gt 0", id="constraint"),
        pytest.param(
            Annotated[int, QueryParameter(lower_case=True)], 5, "lower_case None and lower_case True", id="other-field"
        ),
    ],
)
def test_declarations_differing_raises(provider_annotation: Any, provider_default: Any, message: str) -> None:
    async def provide_value(limit: provider_annotation = provider_default) -> int:  # pyright: ignore[reportInvalidTypeForm]
        return 1

    @get("/", dependencies={"value": Provide(provide_value)})
    async def handler(value: NamedDependency[int], limit: FromQuery[int] = 5) -> None: ...

    with pytest.raises(ImproperlyConfiguredException) as exc_info:
        Litestar([handler], openapi_config=None)
    assert exc_info.value.detail == (
        "[paths='/', handler='handler'] parameter 'limit' of handler 'handler' and parameter 'limit' of provider "
        f"'value' declare the query parameter 'limit' differently: {message}"
    )


def test_declarations_of_two_providers_differing_raises() -> None:
    async def a_dep(query_param: FromQuery[int]) -> int:
        return query_param

    async def b_dep(query_param: FromQuery[str]) -> int:
        return 1

    @get("/test", dependencies={"a": Provide(a_dep), "b": Provide(b_dep)})
    def handler(a: NamedDependency[int], b: NamedDependency[int]) -> str:
        return "OK"

    with pytest.raises(ImproperlyConfiguredException, match="declare the query parameter 'query_param' differently"):
        Litestar([handler], openapi_config=None)


def test_required_and_defaulted_declarations_raises() -> None:
    async def provide_value(limit: FromQuery[int] = 10) -> int:
        return limit

    @get("/", dependencies={"value": Provide(provide_value)})
    async def handler(limit: FromQuery[int], value: NamedDependency[int]) -> None: ...

    with pytest.raises(ImproperlyConfiguredException) as exc_info:
        Litestar([handler], openapi_config=None)
    assert exc_info.value.detail == (
        "[paths='/', handler='handler'] parameter 'limit' of handler 'handler' and parameter 'limit' of provider "
        "'value' declare the query parameter 'limit' differently: no default and default 10"
    )


def test_documentation_set_differently_raises() -> None:
    async def provide_value(limit: Annotated[int, QueryParameter(title="Page limit")]) -> int:
        return limit

    @get("/", dependencies={"value": Provide(provide_value)})
    async def handler(limit: Annotated[int, QueryParameter(title="Limit")], value: NamedDependency[int]) -> None: ...

    with pytest.raises(ImproperlyConfiguredException) as exc_info:
        Litestar([handler], openapi_config=None)
    assert exc_info.value.detail == (
        "[paths='/', handler='handler'] parameter 'limit' of handler 'handler' and parameter 'limit' of provider "
        "'value' declare the query parameter 'limit' differently: title 'Limit' and title 'Page limit'"
    )


def test_documentation_set_by_one_declaration_raises() -> None:
    async def provide_value(limit: FromQuery[int]) -> int:
        return limit

    @get("/", dependencies={"value": Provide(provide_value)})
    async def handler(limit: Annotated[int, QueryParameter(title="Limit")], value: NamedDependency[int]) -> None: ...

    with pytest.raises(ImproperlyConfiguredException) as exc_info:
        Litestar([handler], openapi_config=None)
    assert exc_info.value.detail == (
        "[paths='/', handler='handler'] parameter 'limit' of handler 'handler' and parameter 'limit' of provider "
        "'value' declare the query parameter 'limit' differently: title 'Limit' and title None"
    )


def test_layer_parameter_with_annotation_differing_from_declaration_raises() -> None:
    @get("/")
    async def handler(limit: FromQuery[str]) -> None: ...

    with pytest.raises(ImproperlyConfiguredException) as exc_info:
        Litestar([handler], parameters={"limit": QueryParameter(annotation=int)}, openapi_config=None)
    assert exc_info.value.detail == (
        "[paths='/', handler='handler'] layer parameter 'limit' and parameter 'limit' of handler 'handler' declare "
        "the query parameter 'limit' differently: type 'int' and type 'str'"
    )


def test_provider_bare_marker_not_restating_layer_constraint_raises() -> None:
    async def provide_value(limit: FromQuery[int]) -> int:
        return limit

    @get("/", dependencies={"value": Provide(provide_value)})
    async def handler(value: NamedDependency[int]) -> None: ...

    with pytest.raises(ImproperlyConfiguredException) as exc_info:
        Litestar([handler], parameters={"limit": QueryParameter(gt=0)}, openapi_config=None)
    assert exc_info.value.detail == (
        "[paths='/', handler='handler'] layer parameter 'limit' and parameter 'limit' of provider 'value' declare "
        "the query parameter 'limit' differently: gt 0 and gt None"
    )


def test_handler_constrained_marker_not_restating_layer_constraint_raises() -> None:
    @get("/")
    async def handler(limit: Annotated[int, QueryParameter(lt=5)]) -> None: ...

    with pytest.raises(ImproperlyConfiguredException) as exc_info:
        Litestar([handler], parameters={"limit": QueryParameter(gt=0)}, openapi_config=None)
    assert exc_info.value.detail == (
        "[paths='/', handler='handler'] layer parameter 'limit' and parameter 'limit' of handler 'handler' declare "
        "the query parameter 'limit' differently: gt 0 and gt None"
    )


def test_layer_parameter_documentation_field_set_differently_raises() -> None:
    @get("/")
    async def handler(limit: Annotated[int, QueryParameter(description="Page size")]) -> None: ...

    with pytest.raises(ImproperlyConfiguredException) as exc_info:
        Litestar([handler], parameters={"limit": QueryParameter(description="Limit")}, openapi_config=None)
    assert exc_info.value.detail == (
        "[paths='/', handler='handler'] layer parameter 'limit' and parameter 'limit' of handler 'handler' declare "
        "the query parameter 'limit' differently: description 'Limit' and description 'Page size'"
    )


def test_handler_marker_setting_documentation_field_of_layer_parameter_raises() -> None:
    @get("/")
    async def handler(limit: Annotated[int, QueryParameter(description="Page size")]) -> None: ...

    with pytest.raises(ImproperlyConfiguredException) as exc_info:
        Litestar([handler], parameters={"limit": QueryParameter(annotation=int)}, openapi_config=None)
    assert exc_info.value.detail == (
        "[paths='/', handler='handler'] layer parameter 'limit' and parameter 'limit' of handler 'handler' declare "
        "the query parameter 'limit' differently: description None and description 'Page size'"
    )


def test_required_path_parameter_missing_from_route_raises() -> None:
    async def provide_user(user_id: FromPath[int]) -> int:
        return user_id

    @get("/users", dependencies={"user": Provide(provide_user)})
    async def handler(user: NamedDependency[int]) -> None: ...

    with pytest.raises(ImproperlyConfiguredException) as exc_info:
        Litestar([handler], openapi_config=None)
    assert exc_info.value.detail == (
        "[paths='/users', handler='handler'] parameter 'user_id' of provider 'user' declares the required path "
        "parameter 'user_id', which the route '/users' does not have"
    )


def test_required_path_parameter_missing_from_one_of_handler_paths_raises() -> None:
    async def provide_user(user_id: FromPath[int]) -> int:
        return user_id

    @get(["/users/{user_id:int}", "/users"], dependencies={"user": Provide(provide_user)})
    async def handler(user: NamedDependency[int]) -> None: ...

    with pytest.raises(ImproperlyConfiguredException) as exc_info:
        Litestar([handler], openapi_config=None)
    assert exc_info.value.detail == (
        "[paths='/users,/users/{user_id:int}', handler='handler'] parameter 'user_id' of provider 'user' declares "
        "the required path parameter 'user_id', which the route '/users' does not have"
    )


def test_required_path_parameter_of_handler_missing_from_one_path_raises() -> None:
    @get(["/", "/{user_id:int}"])
    async def handler(user_id: FromPath[int]) -> None: ...

    with pytest.raises(ImproperlyConfiguredException) as exc_info:
        Litestar([handler], openapi_config=None)
    assert exc_info.value.detail == (
        "[paths='/,/{user_id:int}', handler='handler'] parameter 'user_id' of handler 'handler' declares the "
        "required path parameter 'user_id', which the route '/' does not have"
    )


@pytest.mark.parametrize(
    ("provider_annotation", "message"),
    [
        pytest.param(JSONBody[Any], "type 'Person' and type 'Any'", id="any"),  # type: ignore[misc]
        pytest.param(
            MsgPackBody[Person],
            "media_type <RequestEncodingType.JSON: 'application/json'> and media_type "
            "<RequestEncodingType.MESSAGEPACK: 'application/vnd.msgpack'>",
            id="media-type",
        ),
    ],
)
def test_body_declared_differently_raises(provider_annotation: Any, message: str) -> None:
    async def provide_value(data: provider_annotation) -> int:  # pyright: ignore[reportInvalidTypeForm]
        return 1

    @post("/", dependencies={"value": Provide(provide_value)})
    async def handler(data: JSONBody[Person], value: NamedDependency[int]) -> None: ...

    with pytest.raises(ImproperlyConfiguredException) as exc_info:
        Litestar([handler], openapi_config=None)
    assert exc_info.value.detail == (
        "[paths='/', handler='handler'] parameter 'data' of handler 'handler' and parameter 'data' of provider "
        f"'value' declare the request body differently: {message}"
    )
