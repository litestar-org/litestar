import sys
from typing import Dict, Generic, Optional

import pytest
from pydantic import BaseModel
from typing_extensions import Annotated, TypeVar

from litestar._openapi.schema_generation.schema import (
    SchemaCreator,
    _get_type_schema_name,
)
from litestar.contrib.pydantic.pydantic_schema_plugin import PydanticSchemaPlugin
from litestar.contrib.pydantic.utils import PYDANTIC_V2
from litestar.openapi.spec import OpenAPIType
from litestar.openapi.spec.schema import Schema
from litestar.typing import FieldDefinition
from litestar.utils.helpers import get_name

T = TypeVar("T")


class PydanticGeneric(BaseModel, Generic[T]):
    foo: T
    optional_foo: Optional[T]
    annotated_foo: Annotated[T, object()]


@pytest.mark.skipif(
    sys.version_info >= (3, 12) and not PYDANTIC_V2,
    reason="`get_type_hints_with_generics_resolved` does not work. Refer issue #2463.",
)
def test_schema_generation_with_generic_classes() -> None:
    cls = PydanticGeneric[int]
    field_definition = FieldDefinition.from_kwarg(name=get_name(cls), annotation=cls)

    schemas: Dict[str, Schema] = {}
    SchemaCreator(schemas=schemas, plugins=[PydanticSchemaPlugin()]).for_field_definition(field_definition)

    name = _get_type_schema_name(cls)
    properties = schemas[name].properties
    expected_foo_schema = Schema(type=OpenAPIType.INTEGER)
    expected_optional_foo_schema = Schema(one_of=[Schema(type=OpenAPIType.NULL), Schema(type=OpenAPIType.INTEGER)])

    assert properties
    assert properties["foo"] == expected_foo_schema
    assert properties["annotated_foo"] == expected_foo_schema
    assert properties["optional_foo"] == expected_optional_foo_schema
