from dataclasses import dataclass
from datetime import date
from enum import Enum, auto
from typing import TYPE_CHECKING, Dict, List, Literal

import annotated_types
import msgspec
import pydantic
import pytest
from pydantic import BaseModel, Field
from typing_extensions import Annotated, TypeAlias

from litestar import Controller, MediaType, get
from litestar._openapi.schema_generation.schema import (
    KWARG_DEFINITION_ATTRIBUTE_TO_OPENAPI_PROPERTY_MAP,
    SchemaCreator,
    create_schema_for_annotation,
)
from litestar._openapi.schema_generation.utils import normalize_type_name
from litestar.app import DEFAULT_OPENAPI_CONFIG
from litestar.contrib.pydantic import PydanticSchemaPlugin
from litestar.di import Provide
from litestar.enums import ParamType
from litestar.openapi.spec import ExternalDocumentation, OpenAPIType, Reference
from litestar.openapi.spec.example import Example
from litestar.openapi.spec.schema import Schema
from litestar.params import Parameter, ParameterKwarg
from litestar.testing import create_test_client
from litestar.typing import FieldDefinition
from tests import PydanticPerson, PydanticPet

if TYPE_CHECKING:
    from types import ModuleType
    from typing import Callable


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

    assert schema.title  # type: ignore
    assert schema.const == test_str  # type: ignore
    for signature_key, schema_key in KWARG_DEFINITION_ATTRIBUTE_TO_OPENAPI_PROPERTY_MAP.items():
        assert getattr(schema, schema_key) == getattr(kwarg_definition, signature_key)


def test_type_name_normalization() -> None:
    class LocalClass(msgspec.Struct):
        id: str

    assert (
        "_class__tests_unit_test_openapi_test_schema_test_type_name_normalization__locals__LocalClass__"
        == normalize_type_name(str(LocalClass))
    )

    assert "_class__tests_PydanticPerson__" == normalize_type_name(str(PydanticPerson))

    builtin_dict = dict[str, List[int]]
    assert "dict_str__typing_List_int__" == normalize_type_name(str(builtin_dict))

    builtin_with_custom = dict[str, PydanticPerson]
    assert "dict_str__tests_PydanticPerson_" == normalize_type_name(str(builtin_with_custom))


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

    class M(BaseModel):
        opt: Opts

    schema = create_schema_for_annotation(annotation=M.__annotations__["opt"])
    assert schema
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

    schema = schemas[
        "_class__tests_unit_test_openapi_test_schema_test_handling_of_literals__locals__DataclassWithLiteral__"
    ]
    assert isinstance(schema, Schema)
    assert schema.properties

    value = schema.properties["value"]
    assert isinstance(value, Schema)
    assert value.enum == ("a", "b", "c")

    const = schema.properties["const"]
    assert isinstance(const, Schema)
    assert const.const == 1

    composite = schema.properties["composite"]
    assert isinstance(composite, Schema)
    assert composite.enum == ("a", "b", "c", 1)


def test_schema_hashing() -> None:
    schema = Schema(
        one_of=[
            Schema(type=OpenAPIType.STRING),
            Schema(type=OpenAPIType.NUMBER),
            Schema(type=OpenAPIType.OBJECT, properties={"key": Schema(type=OpenAPIType.STRING)}),
        ],
        examples=[Example(value=None), Example(value=[1, 2, 3])],
    )
    assert hash(schema)


def test_title_validation() -> None:
    schemas: Dict[str, Schema] = {}
    schema_creator = SchemaCreator(schemas=schemas, plugins=[PydanticSchemaPlugin()])

    schema_creator.for_field_definition(FieldDefinition.from_kwarg(name="Person", annotation=PydanticPerson))

    assert schemas.get("_class__tests_PydanticPerson__")

    schema_creator.for_field_definition(FieldDefinition.from_kwarg(name="Pet", annotation=PydanticPet))

    assert schemas.get("_class__tests_PydanticPet__")


@pytest.mark.parametrize("with_future_annotations", [True, False])
def test_create_schema_for_pydantic_model_with_annotated_model_attribute(
    with_future_annotations: bool, create_module: "Callable[[str], ModuleType]"
) -> None:
    """Test that a model with an annotated attribute is correctly handled."""
    module = create_module(
        f"""
{'from __future__ import annotations' if with_future_annotations else ''}
from typing_extensions import Annotated
from pydantic import BaseModel

class Foo(BaseModel):
    foo: Annotated[int, "Foo description"]
"""
    )
    schemas: Dict[str, Schema] = {}
    SchemaCreator(schemas=schemas, plugins=[PydanticSchemaPlugin()]).for_field_definition(
        FieldDefinition.from_annotation(module.Foo)
    )
    schema_key = normalize_type_name(str(module.Foo))

    schema = schemas[schema_key]
    assert schema.properties and "foo" in schema.properties


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
    schema_key = normalize_type_name(str(module.Foo))
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
    schema_key = normalize_type_name(str(module.Foo))
    schema = schemas[schema_key]
    assert schema.properties and all(key in schema.properties for key in ("foo", "bar", "baz"))


def test_create_schema_from_msgspec_annotated_type() -> None:
    class Lookup(msgspec.Struct):
        id: Annotated[str, msgspec.Meta(max_length=16, examples=["example"], description="description", title="title")]

    schemas: Dict[str, Schema] = {}
    SchemaCreator(schemas=schemas).for_field_definition(FieldDefinition.from_kwarg(name="Lookup", annotation=Lookup))
    schema = schemas[
        "_class__tests_unit_test_openapi_test_schema_test_create_schema_from_msgspec_annotated_type__locals__Lookup__"
    ]

    assert schema.properties["id"].type == OpenAPIType.STRING  # type: ignore
    assert schema.properties["id"].examples == [Example(value="example")]  # type: ignore
    assert schema.properties["id"].description == "description"  # type: ignore
    assert schema.properties["id"].title == "title"  # type: ignore
    assert schema.properties["id"].max_length == 16  # type: ignore
    assert schema.required == ["id"]


def test_create_schema_for_pydantic_field() -> None:
    class Model(BaseModel):
        if pydantic.VERSION.startswith("1"):
            value: str = Field(
                title="title", description="description", example="example", max_length=16  # pyright: ignore
            )
        else:
            value: str = Field(  # type: ignore[no-redef]
                title="title", description="description", max_length=16, json_schema_extra={"example": "example"}
            )

    schemas: Dict[str, Schema] = {}
    field_definition = FieldDefinition.from_kwarg(name="Model", annotation=Model)
    SchemaCreator(schemas=schemas, plugins=[PydanticSchemaPlugin()]).for_field_definition(field_definition)
    schema = schemas[
        "_class__tests_unit_test_openapi_test_schema_test_create_schema_for_pydantic_field__locals__Model__"
    ]

    assert schema.properties["value"].description == "description"  # type: ignore
    assert schema.properties["value"].title == "title"  # type: ignore
    assert schema.properties["value"].examples == [Example(value="example")]  # type: ignore


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
    schema = schemas["_class__tests_unit_test_openapi_test_schema_test_annotated_types__locals__MyDataclass__"]

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

    @dataclass
    class MyDataclass:
        bar: List[Literal[Foo.A]]

    schemas: Dict[str, Schema] = {}
    SchemaCreator(schemas=schemas).for_field_definition(
        FieldDefinition.from_kwarg(name="MyDataclass", annotation=MyDataclass)
    )
    assert schemas["_class__tests_unit_test_openapi_test_schema_test_literal_enums__locals__MyDataclass__"].properties["bar"].items.const == 1  # type: ignore
