from dataclasses import dataclass
from enum import Enum
from typing import Annotated, Any, Literal, Optional
from uuid import UUID

import msgspec
import pytest

from litestar import get, post
from litestar.exceptions import HTTPException
from litestar.params import Body, JSONBody
from tests.unit.test_openapi.utils import build_document


@dataclass
class Cat:
    name: str


@dataclass
class Dog:
    name: str


@dataclass
class TaggedCat:
    kind: Literal["cat"]
    name: str


@dataclass
class TaggedDog:
    kind: Literal["dog"]
    name: str


@dataclass
class OptionallyTaggedDog:
    name: str
    kind: Literal["dog"] = "dog"


@dataclass
class OtherCat:
    kind: Literal["cat"]
    lives: int


class StructCat(msgspec.Struct, tag="cat"):
    name: str


class StructDog(msgspec.Struct, tag="dog"):
    name: str


class Color(Enum):
    RED = "red"
    BLUE = "blue"


class Shade(Enum):
    NAVY = "navy"
    TEAL = "teal"


class Tone(Enum):
    BLUE = "blue"
    GREY = "grey"


@dataclass
class Branch:
    leaf: "Leaf | None"


@dataclass
class Leaf:
    branch: "Branch | int"


def body_schema(annotation: Any) -> dict[str, Any]:
    @post("/", signature_namespace={"annotation": annotation})
    async def handler(data: JSONBody[annotation]) -> None:  # pyright: ignore
        return None

    document = build_document(handler)
    schema: dict[str, Any] = document["paths"]["/"]["post"]["requestBody"]["content"]["application/json"]["schema"]
    return schema


@pytest.mark.parametrize(
    "annotation",
    [
        int | str,
        Optional[Cat],
        Color | Shade,
        Literal["a"] | int,
        Cat | int | None,
    ],
    ids=["types", "model-or-null", "enums", "literal-and-type", "model-type-null"],
)
def test_union_of_disjoint_members_is_one_of(annotation: Any) -> None:
    schema = body_schema(annotation)

    assert "oneOf" in schema
    assert "anyOf" not in schema


@pytest.mark.parametrize(
    "annotation",
    [UUID | str, int | float, Cat | Dog, Color | Tone, Any | int, list[int] | list[str]],
    ids=["formatted-string", "integer-is-number", "models", "enums-sharing-a-value", "any", "arrays"],
)
def test_union_of_overlapping_members_is_any_of(annotation: Any) -> None:
    schema = body_schema(annotation)

    assert "anyOf" in schema
    assert "oneOf" not in schema


def test_optional_overlapping_union_is_any_of() -> None:
    assert body_schema(Optional[UUID | str]) == {
        "anyOf": [{"type": "string", "format": "uuid"}, {"type": "string"}, {"type": "null"}]
    }


@pytest.mark.parametrize("reverse", [False, True], ids=["branch-first", "leaf-first"])
def test_unions_of_mutually_recursive_models_do_not_depend_on_order(reverse: bool) -> None:
    @post("/branch")
    async def create_branch(data: JSONBody[Branch]) -> None:
        return None

    @post("/leaf")
    async def create_leaf(data: JSONBody[Leaf]) -> None:
        return None

    handlers = [create_branch, create_leaf][:: -1 if reverse else 1]
    components = build_document(*handlers)["components"]["schemas"]

    assert components["Branch"]["properties"]["leaf"] == {
        "oneOf": [{"$ref": "#/components/schemas/Leaf"}, {"type": "null"}]
    }
    assert components["Leaf"]["properties"]["branch"] == {
        "oneOf": [{"$ref": "#/components/schemas/Branch"}, {"type": "integer"}]
    }


def test_user_one_of_with_a_discriminator_is_kept() -> None:
    schema_extra = {
        "one_of": [{"$ref": "#/components/schemas/Cat"}, {"$ref": "#/components/schemas/Dog"}],
        "discriminator": {"propertyName": "name"},
    }

    @post("/")
    async def handler(data: Annotated[Cat | Dog, Body(schema_extra=schema_extra)]) -> None:
        return None

    schema = build_document(handler)["paths"]["/"]["post"]["requestBody"]["content"]["application/json"]["schema"]

    assert "oneOf" in schema
    assert "anyOf" not in schema


def test_error_responses_sharing_a_status_code_are_any_of() -> None:
    class FirstConflict(HTTPException):
        status_code = 409

    class SecondConflict(HTTPException):
        status_code = 409

    @get("/", raises=[FirstConflict, SecondConflict], sync_to_thread=False)
    def handler() -> None:
        return None

    schema = build_document(handler)["paths"]["/"]["get"]["responses"]["409"]["content"]["application/json"]["schema"]

    assert len(schema["anyOf"]) == 2
    assert "oneOf" not in schema


@pytest.mark.parametrize(
    "annotation, keyword",
    [
        (TaggedCat | TaggedDog, "oneOf"),
        (StructCat | StructDog, "oneOf"),
        (TaggedCat | OptionallyTaggedDog, "anyOf"),
        (TaggedCat | OtherCat, "anyOf"),
    ],
    ids=["literal-tags", "msgspec-tags", "optional-tag", "same-tag"],
)
def test_union_of_models_with_distinct_required_tags_is_one_of(annotation: Any, keyword: str) -> None:
    assert list(body_schema(annotation)) == [keyword]
