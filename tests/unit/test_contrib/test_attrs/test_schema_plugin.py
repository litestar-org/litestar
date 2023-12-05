from typing import Generic, Optional

from attrs import define
from typing_extensions import Annotated, TypeVar

from litestar._openapi.schema_generation.schema import (
    SchemaCreator,
)
from litestar.contrib.attrs.attrs_schema_plugin import AttrsSchemaPlugin
from litestar.openapi.spec import OpenAPIType
from litestar.openapi.spec.schema import Schema
from litestar.typing import FieldDefinition
from litestar.utils.helpers import get_name

T = TypeVar("T")


@define
class AttrsGeneric(Generic[T]):
    foo: T
    optional_foo: Optional[T]
    annotated_foo: Annotated[T, object()]


def test_schema_generation_with_generic_classes() -> None:
    cls = AttrsGeneric[int]
    field_definition = FieldDefinition.from_kwarg(name=get_name(cls), annotation=cls)

    creator = SchemaCreator(plugins=[AttrsSchemaPlugin()])
    creator.for_field_definition(field_definition)
    schemas = creator.schema_registry.generate_components_schemas()
    properties = schemas["AttrsGeneric[int]"].properties
    expected_foo_schema = Schema(type=OpenAPIType.INTEGER)
    expected_optional_foo_schema = Schema(one_of=[Schema(type=OpenAPIType.NULL), Schema(type=OpenAPIType.INTEGER)])

    assert properties
    assert properties["foo"] == expected_foo_schema
    assert properties["annotated_foo"] == expected_foo_schema
    assert properties["optional_foo"] == expected_optional_foo_schema
