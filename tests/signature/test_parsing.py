import inspect
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Iterable, List, Literal, Optional, Sequence, cast

import pytest
from pydantic import BaseModel
from typing_extensions import Annotated

from starlite import get
from starlite._signature import create_signature_model
from starlite._signature.parsing.signature_parameter import ParsedSignatureParameter
from starlite._signature.parsing.utils import parse_fn_signature
from starlite.di import Provide
from starlite.exceptions import ImproperlyConfiguredException, ValidationException
from starlite.params import Dependency, Parameter
from starlite.status_codes import HTTP_200_OK, HTTP_204_NO_CONTENT, HTTP_500_INTERNAL_SERVER_ERROR
from starlite.testing import RequestFactory, TestClient, create_test_client
from starlite.types.helper_types import OptionalSequence
from tests.test_plugins import AModel, APlugin

if TYPE_CHECKING:
    from types import ModuleType
    from typing import Callable

    from starlite._signature.models.pydantic_signature_model import PydanticSignatureModel


@pytest.mark.parametrize("preferred_validation_backend", ("attrs", "pydantic"))
def test_parses_values_from_connection_kwargs_with_plugin(
    preferred_validation_backend: Literal["attrs", "pydantic"]
) -> None:
    def fn(a: AModel, b: int) -> None:
        pass

    model = create_signature_model(
        fn=fn,
        plugins=[APlugin()],
        dependency_name_set=set(),
        preferred_validation_backend=preferred_validation_backend,
        signature_namespace={},
    )
    arbitrary_a = {"name": 1}
    result = model.parse_values_from_connection_kwargs(connection=RequestFactory().get(), a=arbitrary_a, b=1)
    assert result == {"a": AModel(name="1"), "b": 1}


@pytest.mark.parametrize("preferred_validation_backend", ("attrs", "pydantic"))
def test_parses_values_from_connection_kwargs_without_plugin(
    preferred_validation_backend: Literal["attrs", "pydantic"]
) -> None:
    class MyModel(BaseModel):
        name: str

    def fn(a: MyModel) -> None:
        pass

    model = create_signature_model(
        fn=fn,
        plugins=[],
        dependency_name_set=set(),
        preferred_validation_backend=preferred_validation_backend,
        signature_namespace={},
    )
    result = model.parse_values_from_connection_kwargs(connection=RequestFactory().get(), a={"name": "my name"})
    assert result == {"a": MyModel(name="my name")}


@pytest.mark.parametrize("preferred_validation_backend", ("attrs", "pydantic"))
def test_parses_values_from_connection_kwargs_raises(
    preferred_validation_backend: Literal["attrs", "pydantic"]
) -> None:
    def fn(a: int) -> None:
        pass

    model = create_signature_model(
        fn=fn,
        plugins=[],
        dependency_name_set=set(),
        preferred_validation_backend=preferred_validation_backend,
        signature_namespace={},
    )
    with pytest.raises(ValidationException):
        model.parse_values_from_connection_kwargs(connection=RequestFactory().get(), a="not an int")


@pytest.mark.parametrize("preferred_validation_backend", ("attrs", "pydantic"))
def test_resolve_field_value(preferred_validation_backend: Literal["attrs", "pydantic"]) -> None:
    def fn(a: AModel, b: int) -> None:
        pass

    model: Any = create_signature_model(
        fn=fn,
        plugins=[APlugin()],
        dependency_name_set=set(),
        preferred_validation_backend=preferred_validation_backend,
        signature_namespace={},
    )
    instance = cast("PydanticSignatureModel", model(a={"name": "my name"}, b=2))
    assert instance._resolve_field_value("a") == AModel(name="my name")
    assert instance._resolve_field_value("b") == 2


@pytest.mark.parametrize("preferred_validation_backend", ("attrs", "pydantic"))
def test_create_function_signature_model_parameter_parsing(
    preferred_validation_backend: Literal["attrs", "pydantic"]
) -> None:
    @get()
    def my_fn(a: int, b: str, c: Optional[bytes], d: bytes = b"123", e: Optional[dict] = None) -> None:
        pass

    model = create_signature_model(
        fn=my_fn.fn.value,
        plugins=[],
        dependency_name_set=set(),
        preferred_validation_backend=preferred_validation_backend,
        signature_namespace={},
    )
    fields = model.fields
    assert fields["a"].field_type is int
    assert not fields["a"].is_optional
    assert fields["b"].field_type is str
    assert not fields["b"].is_optional
    assert fields["c"].field_type is Optional[bytes]
    assert fields["c"].is_optional
    assert fields["c"].default_value is None
    assert fields["d"].field_type is bytes
    assert fields["d"].default_value == b"123"
    assert fields["e"].field_type is Optional[dict]
    assert fields["e"].is_optional
    assert fields["e"].default_value is None


@pytest.mark.parametrize("preferred_validation_backend", ("attrs", "pydantic"))
def test_create_signature_validation(preferred_validation_backend: Literal["attrs", "pydantic"]) -> None:
    @get()
    def my_fn(typed: int, untyped) -> None:  # type: ignore
        pass

    with pytest.raises(ImproperlyConfiguredException):
        create_signature_model(
            fn=my_fn.fn.value,
            plugins=[],
            dependency_name_set=set(),
            preferred_validation_backend=preferred_validation_backend,
            signature_namespace={},
        )


@pytest.mark.parametrize("preferred_validation_backend", ("attrs", "pydantic"))
def test_create_function_signature_model_ignore_return_annotation(
    preferred_validation_backend: Literal["attrs", "pydantic"]
) -> None:
    @get(path="/health", status_code=HTTP_204_NO_CONTENT)
    async def health_check() -> None:
        return None

    signature_model_type = create_signature_model(
        fn=health_check.fn.value,
        plugins=[],
        dependency_name_set=set(),
        preferred_validation_backend=preferred_validation_backend,
        signature_namespace={},
    )
    assert signature_model_type().to_dict() == {}


@pytest.mark.parametrize("preferred_validation_backend", ("attrs", "pydantic"))
def test_create_function_signature_model_validation(preferred_validation_backend: Literal["attrs", "pydantic"]) -> None:
    with pytest.raises(ImproperlyConfiguredException):
        create_signature_model(fn=lru_cache(maxsize=0)(lambda x: x), plugins=[], dependency_name_set=set(), preferred_validation_backend=preferred_validation_backend, signature_namespace={}).dict()  # type: ignore


@pytest.mark.parametrize(
    "preferred_validation_backend, error_extra",
    (
        (
            "attrs",
            [{"key": "dep", "message": "invalid literal for int() with base 10: 'thirteen'"}],
        ),
        (
            "pydantic",
            [{"key": "dep", "message": "value is not a valid integer"}],
        ),
    ),
)
def test_dependency_validation_failure_raises_500(
    preferred_validation_backend: Literal["attrs", "pydantic"],
    error_extra: Any,
) -> None:
    dependencies = {"dep": Provide(lambda: "thirteen")}

    @get("/")
    def test(dep: int, param: int, optional_dep: Optional[int] = Dependency()) -> None:
        ...

    with create_test_client(
        route_handlers=[test], dependencies=dependencies, preferred_validation_backend=preferred_validation_backend
    ) as client:
        response = client.get("/?param=13")

    assert response.json() == {
        "detail": "A dependency failed validation for GET http://testserver.local/?param=13",
        "extra": error_extra,
        "status_code": HTTP_500_INTERNAL_SERVER_ERROR,
    }


@pytest.mark.parametrize(
    "preferred_validation_backend, error_extra",
    (("attrs", [{"key": "param", "message": "invalid literal for int() with base 10: 'thirteen'"}]),),
)
def test_validation_failure_raises_400(
    preferred_validation_backend: Literal["attrs", "pydantic"], error_extra: Any
) -> None:
    dependencies = {"dep": Provide(lambda: 13)}

    @get("/")
    def test(dep: int, param: int, optional_dep: Optional[int] = Dependency()) -> None:
        ...

    with create_test_client(
        route_handlers=[test], dependencies=dependencies, preferred_validation_backend=preferred_validation_backend
    ) as client:
        response = client.get("/?param=thirteen")

    assert response.json() == {
        "detail": "Validation failed for GET http://testserver.local/?param=thirteen",
        "extra": error_extra,
        "status_code": 400,
    }


def test_client_pydantic_backend_error_precedence_over_server_error() -> None:
    dependencies = {"dep": Provide(lambda: "thirteen"), "optional_dep": Provide(lambda: "thirty-one")}

    @get("/")
    def test(dep: int, param: int, optional_dep: Optional[int] = Dependency()) -> None:
        ...

    with create_test_client(
        route_handlers=[test], dependencies=dependencies, preferred_validation_backend="pydantic"
    ) as client:
        response = client.get("/?param=thirteen")

    assert response.json() == {
        "detail": "Validation failed for GET http://testserver.local/?param=thirteen",
        "extra": [{"key": "param", "message": "value is not a valid integer"}],
        "status_code": 400,
    }


def test_signature_model_resolves_forward_ref_annotations(create_module: "Callable[[str], ModuleType]") -> None:
    module = create_module(
        """
from __future__ import annotations

from pydantic import BaseModel
from starlite import Starlite, get
from starlite.di import Provide

class Test(BaseModel):
    hello: str

async def get_dep() -> Test:
    return Test(hello="world")

@get("/", dependencies={"test": Provide(get_dep)})
def hello_world(test: Test) -> Test:
    return test

app = Starlite(route_handlers=[hello_world], openapi_config=None)
"""
    )
    with TestClient(app=module.app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"hello": "world"}


@pytest.mark.parametrize(("query", "exp"), [("?a=1&a=2&a=3", [1, 2, 3]), ("", None)])
def test_parse_optional_sequence_from_connection_kwargs(query: str, exp: Any) -> None:
    @get("/")
    def test(a: Optional[List[int]] = Parameter(query="a", default=None, required=False)) -> Optional[List[int]]:
        return a

    with create_test_client(route_handlers=[test]) as client:
        response = client.get(f"/{query}")
        assert response.status_code == HTTP_200_OK, response.json()
        assert response.json() == exp


@pytest.mark.parametrize("preferred_validation_backend", ("attrs", "pydantic"))
def test_signature_field_is_non_string_iterable(preferred_validation_backend: Literal["attrs", "pydantic"]) -> None:
    def fn(a: Iterable[int], b: Optional[Iterable[int]]) -> None:
        pass

    model = create_signature_model(
        fn=fn,
        plugins=[],
        dependency_name_set=set(),
        preferred_validation_backend=preferred_validation_backend,
        signature_namespace={},
    )

    assert model.fields["a"].is_non_string_iterable
    assert model.fields["b"].is_non_string_iterable


@pytest.mark.parametrize("preferred_validation_backend", ("attrs", "pydantic"))
def test_signature_field_is_non_string_sequence(preferred_validation_backend: Literal["attrs", "pydantic"]) -> None:
    def fn(a: Sequence[int], b: OptionalSequence[int]) -> None:
        pass

    model = create_signature_model(
        fn=fn,
        plugins=[],
        dependency_name_set=set(),
        preferred_validation_backend=preferred_validation_backend,
        signature_namespace={},
    )

    assert model.fields["a"].is_non_string_sequence
    assert model.fields["b"].is_non_string_sequence


def test_parsed_signature_model_from_parameter_resolves_forward_ref() -> None:
    def func(a: "int") -> None:
        ...

    signature = inspect.Signature.from_callable(func)
    obj = object()
    parsed_param = ParsedSignatureParameter.from_parameter("func", "a", signature.parameters["a"], {"a": obj})
    assert parsed_param.annotation is obj


@pytest.mark.parametrize("with_future_annotations", [True, False])
def test_parsed_parameters_with_annotated_types(
    with_future_annotations: bool, create_module: "Callable[[str], ModuleType]"
) -> None:
    module = create_module(
        f"""
{'from __future__ import annotations' if with_future_annotations else ''}
from typing_extensions import Annotated

def fn(a: Annotated[int, "a"]) -> None:
    pass
"""
    )
    (param, *_), _, __, ___ = parse_fn_signature(
        fn=module.fn, plugins=[], dependency_name_set=set(), signature_namespace={}
    )
    assert param.annotation == Annotated[int, "a"]
