import sys
from dataclasses import dataclass
from datetime import date
from enum import Enum, auto
from typing import (  # type: ignore[attr-defined]
    TYPE_CHECKING,
    Any,
    Dict,
    Generic,
    List,
    Literal,
    Optional,
    Tuple,
    TypedDict,
    TypeVar,
    Union,
    _GenericAlias,  # pyright: ignore
)

import annotated_types
import msgspec
import pytest
from msgspec import Struct
from typing_extensions import Annotated, TypeAlias

from litestar import Controller, MediaType, get
from litestar._openapi.schema_generation.schema import (
    KWARG_DEFINITION_ATTRIBUTE_TO_OPENAPI_PROPERTY_MAP,
    SchemaCreator,
)
from litestar._openapi.schema_generation.utils import _get_normalized_schema_key, _type_or_first_not_none_inner_type
from litestar.app import DEFAULT_OPENAPI_CONFIG
from litestar.di import Provide
from litestar.enums import ParamType
from litestar.openapi.spec import ExternalDocumentation, OpenAPIType, Reference
from litestar.openapi.spec.example import Example
from litestar.openapi.spec.schema import Schema
from litestar.pagination import ClassicPagination, CursorPagination, OffsetPagination
from litestar.params import Parameter, ParameterKwarg
from litestar.testing import create_test_client
from litestar.types.builtin_types import NoneType
from litestar.typing import FieldDefinition
from litestar.utils.helpers import get_name
from tests.models import DataclassPerson, DataclassPet

if TYPE_CHECKING:
    from types import ModuleType
    from typing import Callable

T = TypeVar("T")


def test_process_schema_result() -> None:
    test_str = "abc"
    kwarg_definition = ParameterKwarg(
        examples=[Example(value=1)],
        external_docs=ExternalDocumentation(url="https://example.com/docs"),
        content_encoding="utf-8",
        default=test_str,
        title=test_str,
        description=test_str,
        const=True,
        gt=1,
        ge=1,
        lt=1,
        le=1,
        multiple_of=1,
        min_items=1,
        max_items=1,
        min_length=1,
        max_length=1,
        pattern="^[a-z]$",
    )
    field = FieldDefinition.from_annotation(annotation=str, kwarg_definition=kwarg_definition)
    schema = SchemaCreator().for_field_definition(field)

    assert isinstance(schema, Schema)
    assert schema.title
    assert schema.const == test_str
    assert kwarg_definition.examples
    for signature_key, schema_key in KWARG_DEFINITION_ATTRIBUTE_TO_OPENAPI_PROPERTY_MAP.items():
        if schema_key == "examples":
            assert schema.examples == {"str-example-1": kwarg_definition.examples[0]}
        else:
            assert getattr(schema, schema_key) == getattr(kwarg_definition, signature_key)


def test_get_normalized_schema_key() -> None:
    class LocalClass(msgspec.Struct):
        id: str

    assert (
        "tests_unit_test_openapi_test_schema_test_get_normalized_schema_key_locals_LocalClass"
        == _get_normalized_schema_key(str(LocalClass))
    )

    assert "tests_models_DataclassPerson" == _get_normalized_schema_key(str(DataclassPerson))

    builtin_dict = Dict[str, List[int]]
    assert "typing_Dict_str_typing_List_int" == _get_normalized_schema_key(str(builtin_dict))

    builtin_with_custom = Dict[str, DataclassPerson]
    assert "typing_Dict_str_tests_models_DataclassPerson" == _get_normalized_schema_key(str(builtin_with_custom))

    class LocalGeneric(Generic[T]):
        pass

    assert (
        "tests_unit_test_openapi_test_schema_test_get_normalized_schema_key_locals_LocalGeneric"
        == _get_normalized_schema_key(str(LocalGeneric))
    )

    generic_int = LocalGeneric[int]
    generic_str = LocalGeneric[str]

    assert (
        "tests_unit_test_openapi_test_schema_test_get_normalized_schema_key_locals_LocalGeneric_int"
        == _get_normalized_schema_key(str(generic_int))
    )

    assert (
        "tests_unit_test_openapi_test_schema_test_get_normalized_schema_key_locals_LocalGeneric_str"
        == _get_normalized_schema_key(str(generic_str))
    )

    assert _get_normalized_schema_key(str(generic_int)) != _get_normalized_schema_key(str(generic_str))


def test_dependency_schema_generation() -> None:
    async def top_dependency(query_param: int) -> int:
        return query_param

    async def mid_level_dependency(header_param: str = Parameter(header="header_param", required=False)) -> int:
        return 5

    async def local_dependency(path_param: int, mid_level: int, top_level: int) -> int:
        return path_param + mid_level + top_level

    class MyController(Controller):
        path = "/test"
        dependencies = {"mid_level": Provide(mid_level_dependency)}

        @get(
            path="/{path_param:int}",
            dependencies={
                "summed": Provide(local_dependency),
            },
            media_type=MediaType.TEXT,
        )
        def test_function(self, summed: int, handler_param: int) -> str:
            return str(summed)

    with create_test_client(
        MyController,
        dependencies={"top_level": Provide(top_dependency)},
        openapi_config=DEFAULT_OPENAPI_CONFIG,
    ) as client:
        handler = client.app.openapi_schema.paths["/test/{path_param}"]
        data = {param.name: {"in": param.param_in, "required": param.required} for param in handler.get.parameters}
        assert data == {
            "path_param": {"in": ParamType.PATH, "required": True},
            "header_param": {"in": ParamType.HEADER, "required": False},
            "query_param": {"in": ParamType.QUERY, "required": True},
            "handler_param": {"in": ParamType.QUERY, "required": True},
        }


def test_get_schema_for_annotation_enum() -> None:
    class Opts(str, Enum):
        opt1 = "opt1"
        opt2 = "opt2"

    schema = SchemaCreator().for_field_definition(FieldDefinition.from_annotation(Opts))
    assert isinstance(schema, Schema)
    assert schema.enum == ["opt1", "opt2"]


ValueType: TypeAlias = Literal["a", "b", "c"]
ConstType: TypeAlias = Literal[1]


def test_handling_of_literals() -> None:
    @dataclass
    class DataclassWithLiteral:
        value: ValueType
        const: ConstType
        composite: Literal[ValueType, ConstType]

    schemas: Dict[str, Schema] = {}
    result = SchemaCreator(schemas=schemas).for_field_definition(
        FieldDefinition.from_kwarg(name="", annotation=DataclassWithLiteral)
    )
    assert isinstance(result, Reference)

    schema = schemas["tests_unit_test_openapi_test_schema_test_handling_of_literals_locals_DataclassWithLiteral"]
    assert isinstance(schema, Schema)
    assert schema.properties

    value = schema.properties["value"]
    assert isinstance(value, Schema)
    assert value.enum == ["a", "b", "c"]

    const = schema.properties["const"]
    assert isinstance(const, Schema)
    assert const.const == 1

    composite = schema.properties["composite"]
    assert isinstance(composite, Schema)
    assert composite.enum == ["a", "b", "c", 1]


def test_schema_hashing() -> None:
    schema = Schema(
        one_of=[
            Schema(type=OpenAPIType.STRING),
            Schema(type=OpenAPIType.NUMBER),
            Schema(type=OpenAPIType.OBJECT, properties={"key": Schema(type=OpenAPIType.STRING)}),
        ],
        examples={"example-1": Example(value=None), "example-2": Example(value=[1, 2, 3])},
    )
    assert hash(schema)


def test_title_validation() -> None:
    schemas: Dict[str, Schema] = {}
    schema_creator = SchemaCreator(schemas=schemas)

    schema_creator.for_field_definition(FieldDefinition.from_kwarg(name="Person", annotation=DataclassPerson))
    assert schemas.get("tests_models_DataclassPerson")

    schema_creator.for_field_definition(FieldDefinition.from_kwarg(name="Pet", annotation=DataclassPet))
    assert schemas.get("tests_models_DataclassPet")


@pytest.mark.parametrize("with_future_annotations", [True, False])
def test_create_schema_for_dataclass_with_annotated_model_attribute(
    with_future_annotations: bool, create_module: "Callable[[str], ModuleType]"
) -> None:
    """Test that a model with an annotated attribute is correctly handled."""
    module = create_module(
        f"""
{'from __future__ import annotations' if with_future_annotations else ''}
from typing_extensions import Annotated
from dataclasses import dataclass

@dataclass
class Foo:
    foo: Annotated[int, "Foo description"]
"""
    )
    schemas: Dict[str, Schema] = {}
    SchemaCreator(schemas=schemas).for_field_definition(FieldDefinition.from_annotation(module.Foo))
    schema_key = _get_normalized_schema_key(str(module.Foo))
    schema = schemas[schema_key]
    assert schema.properties and "foo" in schema.properties


@pytest.mark.parametrize("with_future_annotations", [True, False])
def test_create_schema_for_typedict_with_annotated_required_and_not_required_model_attributes(
    with_future_annotations: bool, create_module: "Callable[[str], ModuleType]"
) -> None:
    """Test that a model with an annotated attribute is correctly handled."""
    module = create_module(
        f"""
{'from __future__ import annotations' if with_future_annotations else ''}
from typing_extensions import Annotated, Required, NotRequired
from typing import TypedDict

class Foo(TypedDict):
    foo: Annotated[int, "Foo description"]
    bar: Annotated[Required[int], "Bar description"]
    baz: Annotated[NotRequired[int], "Baz description"]
"""
    )
    schemas: Dict[str, Schema] = {}
    SchemaCreator(schemas=schemas).for_field_definition(FieldDefinition.from_annotation(module.Foo))
    schema_key = _get_normalized_schema_key(str(module.Foo))
    schema = schemas[schema_key]
    assert schema.properties and all(key in schema.properties for key in ("foo", "bar", "baz"))


def test_create_schema_from_msgspec_annotated_type() -> None:
    class Lookup(msgspec.Struct):
        id: Annotated[str, msgspec.Meta(max_length=16, examples=["example"], description="description", title="title")]

    schemas: Dict[str, Schema] = {}
    SchemaCreator(schemas=schemas).for_field_definition(FieldDefinition.from_kwarg(name="Lookup", annotation=Lookup))
    schema = schemas["tests_unit_test_openapi_test_schema_test_create_schema_from_msgspec_annotated_type_locals_Lookup"]

    assert schema.properties["id"].type == OpenAPIType.STRING  # type: ignore
    assert schema.properties["id"].examples == {"id-example-1": Example(value="example")}  # type: ignore
    assert schema.properties["id"].description == "description"  # type: ignore
    assert schema.properties["id"].title == "title"  # type: ignore
    assert schema.properties["id"].max_length == 16  # type: ignore
    assert schema.required == ["id"]


def test_annotated_types() -> None:
    historical_date = date(year=1980, day=1, month=1)
    today = date.today()

    @dataclass
    class MyDataclass:
        constrained_int: Annotated[int, annotated_types.Gt(1), annotated_types.Lt(10)]
        constrained_float: Annotated[float, annotated_types.Ge(1), annotated_types.Le(10)]
        constrained_date: Annotated[date, annotated_types.Interval(gt=historical_date, lt=today)]
        constrainted_lower_case: Annotated[str, annotated_types.LowerCase]
        constrainted_upper_case: Annotated[str, annotated_types.UpperCase]
        constrainted_is_ascii: Annotated[str, annotated_types.IsAscii]
        constrainted_is_digit: Annotated[str, annotated_types.IsDigits]

    schemas: Dict[str, Schema] = {}
    SchemaCreator(schemas=schemas).for_field_definition(
        FieldDefinition.from_kwarg(name="MyDataclass", annotation=MyDataclass)
    )
    schema = schemas["tests_unit_test_openapi_test_schema_test_annotated_types_locals_MyDataclass"]

    assert schema.properties["constrained_int"].exclusive_minimum == 1  # type: ignore
    assert schema.properties["constrained_int"].exclusive_maximum == 10  # type: ignore
    assert schema.properties["constrained_float"].minimum == 1  # type: ignore
    assert schema.properties["constrained_float"].maximum == 10  # type: ignore
    assert date.fromtimestamp(schema.properties["constrained_date"].exclusive_minimum) == historical_date  # type: ignore
    assert date.fromtimestamp(schema.properties["constrained_date"].exclusive_maximum) == today  # type: ignore
    assert schema.properties["constrainted_lower_case"].description == "must be in lower case"  # type: ignore
    assert schema.properties["constrainted_upper_case"].description == "must be in upper case"  # type: ignore
    assert schema.properties["constrainted_is_ascii"].pattern == "[[:ascii:]]"  # type: ignore
    assert schema.properties["constrainted_is_digit"].pattern == "[[:digit:]]"  # type: ignore


def test_literal_enums() -> None:
    class Foo(Enum):
        A = auto()
        B = auto()

    schema = SchemaCreator().for_field_definition(FieldDefinition.from_annotation(List[Literal[Foo.A]]))
    assert isinstance(schema, Schema)
    assert isinstance(schema.items, Schema)
    assert schema.items.const == 1


@dataclass
class DataclassGeneric(Generic[T]):
    foo: T
    optional_foo: Optional[T]
    annotated_foo: Annotated[T, object()]


class MsgspecGeneric(Struct, Generic[T]):
    foo: T
    optional_foo: Optional[T]
    annotated_foo: Annotated[T, object()]


annotations: List[type] = [DataclassGeneric[int], MsgspecGeneric[int]]

# Generic TypedDict was only supported from 3.11 onwards
if sys.version_info >= (3, 11):

    class TypedDictGeneric(TypedDict, Generic[T]):
        foo: T
        optional_foo: Optional[T]
        annotated_foo: Annotated[T, object()]

    annotations.append(TypedDictGeneric[int])


@pytest.mark.parametrize("cls", annotations)
def test_schema_generation_with_generic_classes(cls: Any) -> None:
    field_definition = FieldDefinition.from_kwarg(name=get_name(cls), annotation=cls)

    schemas: Dict[str, Schema] = {}
    SchemaCreator(schemas=schemas).for_field_definition(field_definition)

    path_name = _get_normalized_schema_key(str(cls))
    properties = schemas[path_name].properties
    expected_foo_schema = Schema(type=OpenAPIType.INTEGER)
    expected_optional_foo_schema = Schema(one_of=[Schema(type=OpenAPIType.NULL), Schema(type=OpenAPIType.INTEGER)])

    assert properties
    assert properties["foo"] == expected_foo_schema
    assert properties["annotated_foo"] == expected_foo_schema
    assert properties["optional_foo"] == expected_optional_foo_schema


B = TypeVar("B", bound=int)
C = TypeVar("C", int, str)


@dataclass
class ConstrainedGenericDataclass(Generic[T, B, C]):
    bound: B
    constrained: C
    union: Union[T, bool]
    union_constrained: Union[C, bool]
    union_bound: Union[B, bool]


def test_schema_generation_with_generic_classes_constrained() -> None:
    cls = ConstrainedGenericDataclass
    field_definition = FieldDefinition.from_kwarg(name=cls.__name__, annotation=cls)

    schemas: Dict[str, Schema] = {}
    SchemaCreator(schemas=schemas).for_field_definition(field_definition)

    properties = schemas["tests_unit_test_openapi_test_schema_ConstrainedGenericDataclass"].properties

    assert properties
    assert properties["bound"] == Schema(type=OpenAPIType.INTEGER)
    assert properties["constrained"] == Schema(
        one_of=[Schema(type=OpenAPIType.INTEGER), Schema(type=OpenAPIType.STRING)]
    )
    assert properties["union"] == Schema(one_of=[Schema(type=OpenAPIType.OBJECT), Schema(type=OpenAPIType.BOOLEAN)])
    assert properties["union_constrained"] == Schema(
        one_of=[Schema(type=OpenAPIType.INTEGER), Schema(type=OpenAPIType.STRING), Schema(type=OpenAPIType.BOOLEAN)]
    )
    assert properties["union_bound"] == Schema(
        one_of=[Schema(type=OpenAPIType.INTEGER), Schema(type=OpenAPIType.BOOLEAN)]
    )


@pytest.mark.parametrize(
    "annotation",
    (
        ClassicPagination[DataclassGeneric[int]],
        OffsetPagination[DataclassGeneric[int]],
        CursorPagination[int, DataclassGeneric[int]],
    ),
)
def test_schema_generation_with_pagination(annotation: Any) -> None:
    field_definition = FieldDefinition.from_annotation(annotation)
    schemas: Dict[str, Schema] = {}
    SchemaCreator(schemas=schemas).for_field_definition(field_definition)
    schema_key = _get_normalized_schema_key(str(field_definition.inner_types[-1].annotation))
    properties = schemas[str(schema_key)].properties

    expected_foo_schema = Schema(type=OpenAPIType.INTEGER)
    expected_optional_foo_schema = Schema(one_of=[Schema(type=OpenAPIType.NULL), Schema(type=OpenAPIType.INTEGER)])

    assert properties
    assert properties["foo"] == expected_foo_schema
    assert properties["annotated_foo"] == expected_foo_schema
    assert properties["optional_foo"] == expected_optional_foo_schema


def test_schema_generation_with_ellipsis() -> None:
    schema = SchemaCreator().for_field_definition(FieldDefinition.from_annotation(Tuple[int, ...]))
    assert isinstance(schema, Schema)
    assert isinstance(schema.items, Schema)
    assert schema.items.type == OpenAPIType.INTEGER


def test_schema_tuple_with_union() -> None:
    schema = SchemaCreator().for_field_definition(FieldDefinition.from_annotation(Tuple[int, Union[int, str]]))
    assert isinstance(schema, Schema)
    assert isinstance(schema.items, Schema)
    assert schema.items.one_of == [
        Schema(type=OpenAPIType.INTEGER),
        Schema(one_of=[Schema(type=OpenAPIType.INTEGER), Schema(type=OpenAPIType.STRING)]),
    ]


def test_optional_enum() -> None:
    class Foo(Enum):
        A = 1
        B = 2

    schema = SchemaCreator().for_field_definition(FieldDefinition.from_annotation(Optional[Foo]))
    assert isinstance(schema, Schema)
    assert schema.type == OpenAPIType.INTEGER
    assert schema.enum == [1, 2, None]


def test_optional_literal() -> None:
    schema = SchemaCreator().for_field_definition(FieldDefinition.from_annotation(Optional[Literal[1]]))
    assert isinstance(schema, Schema)
    assert schema.type == OpenAPIType.INTEGER
    assert schema.enum == [1, None]


@pytest.mark.parametrize(
    ("in_type", "out_type"),
    [
        (FieldDefinition.from_annotation(Optional[int]), int),
        (FieldDefinition.from_annotation(Union[None, int]), int),
        (FieldDefinition.from_annotation(int), int),
        # hack to create a union of NoneType, NoneType to hit a branch for coverage
        (FieldDefinition.from_annotation(_GenericAlias(Union, (NoneType, NoneType))), ValueError),
    ],
)
def test_type_or_first_not_none_inner_type_utility(in_type: Any, out_type: Any) -> None:
    if out_type is ValueError:
        with pytest.raises(out_type):
            _type_or_first_not_none_inner_type(in_type)
    else:
        assert _type_or_first_not_none_inner_type(in_type) == out_type
