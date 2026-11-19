import dataclasses
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Annotated, Any, Optional, Union
from uuid import UUID

import annotated_types
import pytest

from litestar import get, post
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.params import Body, KwargDefinition, QueryParameter
from litestar.testing import create_test_client
from tests.unit.test_openapi.utils import build_document

BOUND_KEYWORDS = {"minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf"}
DECIMAL = {
    "oneOf": [
        {"type": "number"},
        {"type": "string", "pattern": r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$"},
    ]
}


def get_properties(*fields: tuple[str, Any]) -> dict[str, Any]:
    model = dataclasses.make_dataclass("Model", fields)

    @get("/", sync_to_thread=False)
    def handler() -> model:  # type: ignore[valid-type]
        raise NotImplementedError

    properties: dict[str, Any] = build_document(handler)["components"]["schemas"]["Model"]["properties"]
    return properties


@pytest.mark.parametrize(
    ("annotation", "constraint"),
    [
        (bool, KwargDefinition(const=True)),
        (date, annotated_types.Ge(date(2020, 1, 1))),
        (Optional[date], annotated_types.Ge(date(2020, 1, 1))),
        (datetime, annotated_types.Gt(datetime(2020, 1, 1))),
        (Optional[datetime], annotated_types.Gt(datetime(2020, 1, 1))),
        (time, annotated_types.Gt(time(1))),
        (timedelta, annotated_types.Gt(timedelta(1))),
        (UUID, KwargDefinition(pattern="^[0-9a-f-]+$")),
    ],
)
def test_constrained_scalar_keeps_type_and_format(annotation: Any, constraint: Any) -> None:
    properties = get_properties(("constrained", Annotated[annotation, constraint]), ("plain", annotation))

    assert {key: properties["constrained"].get(key) for key in ("type", "format")} == {
        key: properties["plain"].get(key) for key in ("type", "format")
    }
    assert not BOUND_KEYWORDS & properties["constrained"].keys()


def test_constrained_any_is_not_an_array() -> None:
    assert get_properties(("anything", Annotated[Any, annotated_types.MinLen(1)])) == {"anything": {"minLength": 1}}


def test_date_bounds_are_described() -> None:
    assert get_properties(
        ("day", Annotated[date, annotated_types.Ge(date(2020, 1, 1))]),
        ("maybe_day", Annotated[Optional[date], annotated_types.Ge(date(2020, 1, 1))]),
        ("moment", Annotated[datetime, annotated_types.Interval(gt=datetime(2020, 1, 1), le=datetime(2030, 1, 1))]),
        (
            "described",
            Annotated[date, KwargDefinition(description="Start of the period"), annotated_types.Ge(date(2020, 1, 1))],
        ),
        ("day_or_number", Annotated[Union[date, int, None], annotated_types.Ge(date(2020, 1, 1))]),
    ) == {
        "day": {"type": "string", "format": "date", "description": "must be on or after 2020-01-01"},
        "maybe_day": {"type": ["string", "null"], "format": "date", "description": "must be on or after 2020-01-01"},
        "moment": {
            "type": "string",
            "format": "date-time",
            "description": "must be after 2020-01-01T00:00:00 and on or before 2030-01-01T00:00:00",
        },
        "described": {"type": "string", "format": "date", "description": "Start of the period"},
        "day_or_number": {
            "oneOf": [{"type": "string", "format": "date"}, {"type": "integer"}, {"type": "null"}],
            "description": "must be on or after 2020-01-01",
        },
    }


def test_decimal_is_documented_as_number_or_decimal_string() -> None:
    assert get_properties(
        ("plain", Decimal),
        ("positive", Annotated[Decimal, annotated_types.Gt(0)]),
        ("bounded", Annotated[Decimal, annotated_types.Interval(ge=Decimal("1.5"), lt=10)]),
        ("optional", Annotated[Optional[Decimal], annotated_types.Gt(Decimal("1.5"))]),
        ("cents", Annotated[Decimal, annotated_types.MultipleOf(Decimal("0.01"))]),
    ) == {
        "plain": DECIMAL,
        "positive": {**DECIMAL, "exclusiveMinimum": 0},
        "bounded": {**DECIMAL, "minimum": 1.5, "exclusiveMaximum": 10},
        "optional": {"oneOf": [*DECIMAL["oneOf"], {"type": "null"}], "exclusiveMinimum": 1.5},
        "cents": {**DECIMAL, "multipleOf": 0.01},
    }


def test_numeric_bounds_are_documented_on_numeric_schemas() -> None:
    properties = get_properties(
        ("integer", Annotated[int, annotated_types.Ge(1)]),
        ("number", Annotated[float, annotated_types.Gt(Decimal("1.5"))]),
        ("optional_integer", Annotated[Optional[int], annotated_types.Le(10)]),
        ("optional_number", Annotated[Optional[float], annotated_types.Lt(Decimal("2.5"))]),
        ("optional_zero", Annotated[Optional[int], annotated_types.Ge(0)]),
        ("integer_or_string", Annotated[int | str, annotated_types.Ge(1)]),
        ("string", Annotated[str, KwargDefinition(ge=1)]),
    )

    assert properties == {
        "integer": {"type": "integer", "minimum": 1.0},
        "number": {"type": "number", "exclusiveMinimum": 1.5},
        "optional_integer": {"type": ["integer", "null"], "maximum": 10},
        "optional_number": {"type": ["number", "null"], "exclusiveMaximum": 2.5},
        "optional_zero": {"type": ["integer", "null"], "minimum": 0},
        "integer_or_string": {"oneOf": [{"type": "integer"}, {"type": "string"}], "minimum": 1},
        "string": {"type": "string"},
    }
    assert type(properties["optional_number"]["exclusiveMaximum"]) is float


def test_constrained_bool_parameter_is_boolean() -> None:
    @get("/", sync_to_thread=False)
    def handler(flag: Annotated[bool, QueryParameter(const=True)] = True) -> None:
        return None

    (parameter,) = build_document(handler)["paths"]["/"]["get"]["parameters"]

    assert parameter["schema"] == {"type": "boolean", "const": True, "default": True}


@dataclass
class Nested:
    value: int


def test_constrained_collections_keep_their_shape() -> None:
    assert get_properties(
        ("mapping", Annotated[dict[str, int], annotated_types.MinLen(1)]),
        ("mapping_items", Annotated[dict[str, int], KwargDefinition(min_items=1, max_items=3)]),
        ("bare_mapping", Annotated[dict, annotated_types.MaxLen(2)]),
        ("optional_mapping", Annotated[Optional[dict[str, int]], annotated_types.MinLen(1)]),
        ("variadic_tuple", Annotated[tuple[int, ...], annotated_types.MinLen(1)]),
        ("sequence", Annotated[list[int], annotated_types.Len(1, 3)]),
        ("sequence_of_union", Annotated[list[int | str], annotated_types.MinLen(1)]),
        ("sequence_length", Annotated[list[int], KwargDefinition(min_length=1, max_length=2)]),
        ("bare_sequence", Annotated[list, annotated_types.MinLen(1)]),
        ("optional_sequence", Annotated[Optional[list[int]], annotated_types.MinLen(2)]),
        ("unique", Annotated[set[int], annotated_types.MaxLen(3)]),
        ("frozen_unique", Annotated[frozenset[int], annotated_types.MinLen(1)]),
        ("string_items", Annotated[str, KwargDefinition(min_items=1)]),
    ) == {
        "mapping": {"type": "object", "additionalProperties": {"type": "integer"}, "minProperties": 1},
        "mapping_items": {
            "type": "object",
            "additionalProperties": {"type": "integer"},
            "minProperties": 1,
            "maxProperties": 3,
        },
        "bare_mapping": {"type": "object", "maxProperties": 2},
        "optional_mapping": {
            "oneOf": [{"type": "object", "additionalProperties": {"type": "integer"}}, {"type": "null"}],
            "minProperties": 1,
        },
        "variadic_tuple": {"type": "array", "items": {"type": "integer"}, "minItems": 1},
        "sequence": {"type": "array", "items": {"type": "integer"}, "minItems": 1, "maxItems": 3},
        "sequence_of_union": {
            "type": "array",
            "items": {"oneOf": [{"type": "integer"}, {"type": "string"}]},
            "minItems": 1,
        },
        "sequence_length": {"type": "array", "items": {"type": "integer"}, "minItems": 1, "maxItems": 2},
        "bare_sequence": {"type": "array", "minItems": 1},
        "optional_sequence": {
            "oneOf": [{"type": "array", "items": {"type": "integer"}}, {"type": "null"}],
            "minItems": 2,
        },
        "unique": {"type": "array", "items": {"type": "integer"}, "maxItems": 3, "uniqueItems": True},
        "frozen_unique": {"type": "array", "items": {"type": "integer"}, "minItems": 1, "uniqueItems": True},
        "string_items": {"type": "string", "minLength": 1},
    }


def test_constrained_fixed_tuple_keeps_prefix_items() -> None:
    properties = get_properties(("pair", Annotated[tuple[int, str], KwargDefinition(description="pair", min_items=2)]))

    assert properties["pair"]["prefixItems"] == [{"type": "integer"}, {"type": "string"}]
    assert properties["pair"]["minItems"] == 2
    assert properties["pair"]["description"] == "pair"
    assert "items" not in properties["pair"]


def test_length_constraint_keeps_its_keyword_when_the_shape_is_unknown() -> None:
    assert get_properties(
        ("anything", Annotated[Any, annotated_types.MinLen(1)]),
        ("string_or_sequence", Annotated[str | list[int], annotated_types.MinLen(1)]),
        ("optional_model", Annotated[Optional[Nested], annotated_types.MinLen(1)]),
    ) == {
        "anything": {"minLength": 1},
        "string_or_sequence": {
            "oneOf": [{"type": "string"}, {"type": "array", "items": {"type": "integer"}}],
            "minLength": 1,
        },
        "optional_model": {"oneOf": [{"$ref": "#/components/schemas/Nested"}, {"type": "null"}], "minLength": 1},
    }


def test_constrained_mapping_body_matches_the_server() -> None:
    @post("/", sync_to_thread=False)
    def handler(data: Annotated[dict[str, int], Body(min_items=1, max_items=2)]) -> None:
        return None

    with create_test_client(handler) as client:
        operation = client.app.openapi_schema.to_schema()["paths"]["/"]["post"]
        assert operation["requestBody"]["content"]["application/json"]["schema"] == {
            "type": "object",
            "additionalProperties": {"type": "integer"},
            "minProperties": 1,
            "maxProperties": 2,
        }
        assert client.post("/", json={"a": 1}).status_code == 201
        assert client.post("/", json={}).status_code == 400
        assert client.post("/", json={"a": 1, "b": 2, "c": 3}).status_code == 400


def test_constrained_collection_items_have_no_generated_examples() -> None:
    @post("/", sync_to_thread=False)
    def handler(data: Annotated[dict[str, int], Body(min_items=1)]) -> None:
        return None

    operation = build_document(handler, create_examples=True)["paths"]["/"]["post"]
    schema = operation["requestBody"]["content"]["application/json"]["schema"]

    assert schema["type"] == "object"
    assert schema["additionalProperties"] == {"type": "integer"}


def test_constrained_upload_collection_bounds_the_files_property() -> None:
    @post("/constrained", sync_to_thread=False)
    def constrained(
        data: Annotated[list[UploadFile], Body(media_type=RequestEncodingType.MULTI_PART, min_items=2)],
    ) -> None:
        return None

    @post("/plain", sync_to_thread=False)
    def plain(data: Annotated[list[UploadFile], Body(media_type=RequestEncodingType.MULTI_PART)]) -> None:
        return None

    with create_test_client([constrained, plain]) as client:
        paths = client.app.openapi_schema.to_schema()["paths"]
        constrained_schema, plain_schema = (
            paths[path]["post"]["requestBody"]["content"]["multipart/form-data"]["schema"]
            for path in ("/constrained", "/plain")
        )
        assert constrained_schema == {
            "type": "object",
            "properties": {"files": {**plain_schema["properties"]["files"], "minItems": 2}},
        }
        assert client.post("/constrained", files=[("files", ("a.txt", b"a"))]).status_code == 400
        two_files = [("files", ("a.txt", b"a")), ("files", ("b.txt", b"b"))]
        assert client.post("/constrained", files=two_files).status_code == 201


@pytest.mark.parametrize(
    "annotation",
    [
        Annotated[list[UploadFile], Body(media_type=RequestEncodingType.MULTI_PART, min_items=2, max_items=3)],
        Annotated[list[UploadFile], Body(media_type=RequestEncodingType.MULTI_PART, min_length=2, max_length=3)],
        Annotated[dict[str, UploadFile], Body(media_type=RequestEncodingType.MULTI_PART, min_items=2, max_items=3)],
        Annotated[
            Optional[list[UploadFile]], Body(media_type=RequestEncodingType.MULTI_PART, min_items=2, max_items=3)
        ],
    ],
)
def test_upload_collection_bounds_match_the_server(annotation: Any) -> None:
    def upload(data: Any) -> None:
        return None

    upload.__annotations__["data"] = annotation

    with create_test_client([post("/upload", sync_to_thread=False)(upload)]) as client:
        schema = client.app.openapi_schema.to_schema()["paths"]["/upload"]["post"]["requestBody"]["content"][
            "multipart/form-data"
        ]["schema"]
        files_schema = schema["properties"]["files"]
        assert (files_schema["minItems"], files_schema["maxItems"]) == (2, 3)
        for count, status in ((1, 400), (2, 201), (3, 201), (4, 400)):
            files = [(f"file{index}", (f"{index}.txt", b"x")) for index in range(count)]
            assert client.post("/upload", files=files).status_code == status
