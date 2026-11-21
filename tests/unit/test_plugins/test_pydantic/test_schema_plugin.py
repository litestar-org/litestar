import datetime
from decimal import Decimal
from typing import Annotated, Any, Generic, Literal, Optional, TypeVar, Union

import pydantic as pydantic_v2
import pytest

from litestar.openapi.spec import OpenAPIType
from litestar.plugins.pydantic import PydanticSchemaPlugin
from litestar.typing import FieldDefinition
from tests.helpers import get_schema_for_field_definition
from tests.unit.test_plugins.test_pydantic import pydantic_document

T = TypeVar("T")


class PydanticV2Generic(pydantic_v2.BaseModel, Generic[T]):
    foo: T
    optional_foo: Optional[T]
    annotated_foo: Annotated[T, object()]


def test_schema_generation_with_generic_classes() -> None:
    schemas = pydantic_document(PydanticV2Generic[int], response=False)["components"]["schemas"]
    properties = schemas["PydanticV2Generic_int_"]["properties"]

    assert properties["foo"] == {"title": "Foo", "type": "integer"}
    assert properties["annotated_foo"] == {"title": "Annotated Foo", "type": "integer"}
    assert properties["optional_foo"] == {"anyOf": [{"type": "integer"}, {"type": "null"}], "title": "Optional Foo"}


@pytest.mark.parametrize(
    "constrained",
    [
        pydantic_v2.constr(pattern="^[a-zA-Z]$"),
        pydantic_v2.conlist(int, min_length=1),
        pydantic_v2.conset(int, min_length=1),
        pydantic_v2.conint(gt=10, lt=100),
        pydantic_v2.confloat(ge=10, le=100),
        pydantic_v2.condecimal(gt=Decimal("10")),
        pydantic_v2.condate(gt=datetime.date.today()),
    ],
)
def test_is_pydantic_constrained_field(constrained: Any) -> None:
    PydanticSchemaPlugin.is_constrained_field(FieldDefinition.from_annotation(constrained))


def test_v2_constrained_secrets() -> None:
    # https://github.com/litestar-org/litestar/issues/3148
    class Model(pydantic_v2.BaseModel):
        string: pydantic_v2.SecretStr = pydantic_v2.Field(min_length=1)
        bytes_: pydantic_v2.SecretBytes = pydantic_v2.Field(min_length=1)

    properties = pydantic_document(Model)["components"]["schemas"]["Model"]["properties"]

    secret = {"type": "string", "minLength": 1, "format": "password", "writeOnly": True}
    assert properties == {"string": {**secret, "title": "String"}, "bytes_": {**secret, "title": "Bytes"}}


class V2ModelWithPrivateFields(pydantic_v2.BaseModel):
    _field: str = pydantic_v2.PrivateAttr()
    # include an invalid annotation here to ensure we never touch those fields
    _underscore_field: str = "foo"


class V2GenericModelWithPrivateFields(pydantic_v2.BaseModel, Generic[T]):
    _field: str = pydantic_v2.PrivateAttr()
    # include an invalid annotation here to ensure we never touch those fields
    _underscore_field: str = "foo"


@pytest.mark.parametrize(
    "model_class",
    [
        V2ModelWithPrivateFields,
        V2GenericModelWithPrivateFields,
    ],
)
def test_exclude_private_fields(model_class: type[pydantic_v2.BaseModel]) -> None:
    # https://github.com/litestar-org/litestar/issues/3150
    schemas = pydantic_document(model_class)["components"]["schemas"]

    assert schemas[model_class.__name__]["properties"] == {}


class NumberList(pydantic_v2.RootModel[list[int]]):
    pass


class StringDict(pydantic_v2.RootModel[dict[str, str]]):
    pass


class BasePet(pydantic_v2.BaseModel):
    name: str


class Cat(BasePet):
    pet_type: Literal["cat"]


class Lizard(BasePet):
    pet_type: Literal["reptile", "lizard"]


class Pet(pydantic_v2.RootModel[BasePet]):
    root: Annotated[  # pyright: ignore[reportIncompatibleVariableOverride]
        Union[Annotated[Cat, pydantic_v2.Tag("cat")], Annotated[Lizard, pydantic_v2.Tag("lizard")]],
        pydantic_v2.Field(discriminator="pet_type"),
    ]


class PetStore(pydantic_v2.BaseModel):
    pets: list[Pet]


@pytest.mark.parametrize(
    "model, expected",
    [
        (NumberList, {"NumberList": {"items": {"type": "integer"}, "type": "array", "title": "NumberList"}}),
        (
            StringDict,
            {"StringDict": {"additionalProperties": {"type": "string"}, "type": "object", "title": "StringDict"}},
        ),
    ],
)
def test_root_model_schema_generation(model: Any, expected: dict[str, Any]) -> None:
    assert pydantic_document(model, response=False)["components"]["schemas"] == expected


def test_root_model_of_a_discriminated_union() -> None:
    schemas = pydantic_document(PetStore, response=False)["components"]["schemas"]

    assert set(schemas) == {"PetStore", "Pet", "Cat", "Lizard"}
    assert schemas["PetStore"]["properties"]["pets"]["items"] == {"$ref": "#/components/schemas/Pet"}
    assert schemas["Pet"] == {
        "oneOf": [{"$ref": "#/components/schemas/Cat"}, {"$ref": "#/components/schemas/Lizard"}],
        "title": "Pet",
        "discriminator": {
            "propertyName": "pet_type",
            "mapping": {
                "cat": "#/components/schemas/Cat",
                "lizard": "#/components/schemas/Lizard",
                "reptile": "#/components/schemas/Lizard",
            },
        },
    }
    assert schemas["Lizard"]["properties"]["pet_type"] == {
        "type": "string",
        "enum": ["reptile", "lizard"],
        "title": "Pet Type",
    }


def test_optional_pydantic_type_does_not_change_the_required_schema() -> None:
    optional = get_schema_for_field_definition(
        FieldDefinition.from_annotation(Optional[pydantic_v2.EmailStr]), plugins=[PydanticSchemaPlugin()]
    )
    required = get_schema_for_field_definition(
        FieldDefinition.from_annotation(pydantic_v2.EmailStr), plugins=[PydanticSchemaPlugin()]
    )

    assert optional.type == [OpenAPIType.STRING, OpenAPIType.NULL]
    assert required.type == OpenAPIType.STRING
