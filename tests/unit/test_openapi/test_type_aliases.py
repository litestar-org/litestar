import dataclasses
import sys
from typing import Annotated, Any, Optional

import annotated_types
import msgspec
import pydantic
import pytest

from litestar import get, post
from litestar.exceptions import ImproperlyConfiguredException
from litestar.handlers import HTTPRouteHandler
from litestar.params import FromQuery, JSONBody, QueryParameter
from litestar.testing import create_test_client
from tests.unit.test_openapi.utils import build_document

pytestmark = pytest.mark.skipif(sys.version_info < (3, 12), reason="type statement not available before 3.12")

PAIR = "type Pair[T] = tuple[T, T]"


def evaluate(source: str, expression: str) -> Any:
    namespace: dict[str, Any] = {
        "__name__": __name__,
        "Annotated": Annotated,
        "annotated_types": annotated_types,
        "pydantic": pydantic,
    }
    exec(source, namespace)
    return eval(expression, namespace)


def make_model(library: str, annotation: Any) -> Any:
    if library == "dc":
        return dataclasses.make_dataclass("Model", [("x", annotation)])
    if library == "ms":
        return msgspec.defstruct("Model", [("x", annotation)])
    return pydantic.create_model("Model", x=(annotation, ...))


def accepting(path: str, annotation: Any) -> HTTPRouteHandler:
    @post(path)
    async def handler(data: JSONBody[annotation]) -> None:  # pyright: ignore[reportInvalidTypeForm]
        return None

    return handler


def returning(path: str, annotation: Any, value: Any = None) -> HTTPRouteHandler:
    @get(path)
    async def handler() -> annotation:  # pyright: ignore[reportInvalidTypeForm]
        return value

    return handler


def body_schema(annotation: Any, **config: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    document = build_document(accepting("/", annotation), **config)
    return (
        document["paths"]["/"]["post"]["requestBody"]["content"]["application/json"]["schema"],
        document["components"]["schemas"],
    )


@pytest.mark.parametrize(
    ("source", "expression", "equivalent"),
    [
        pytest.param(PAIR, "Pair[int]", tuple[int, int], id="one-parameter"),
        pytest.param("type Swapped[K, V] = dict[V, K]", "Swapped[int, str]", dict[str, int], id="parameter-order"),
        pytest.param(f"{PAIR}\ntype Pairs[T] = list[Pair[T]]", "Pairs[int]", list[tuple[int, int]], id="nested"),
        pytest.param(
            "type Map[K, V] = dict[K, V]\ntype StrMap[V] = Map[str, V]",
            "StrMap[int]",
            dict[str, int],
            id="partially-applied",
        ),
        pytest.param("type Maybe[T] = T | None", "Maybe[int]", Optional[int], id="union"),
        pytest.param(
            "type Box[T] = Annotated[list[T], annotated_types.MinLen(1)]",
            "Box[int]",
            Annotated[list[int], annotated_types.MinLen(1)],
            id="annotated",
        ),
        pytest.param(
            "type Map[K, V = int] = dict[K, V]",
            "Map[str]",
            dict[str, int],
            id="type-parameter-default",
            marks=pytest.mark.skipif(
                sys.version_info < (3, 13), reason="type parameter defaults are not available before 3.13"
            ),
        ),
    ],
)
def test_generic_type_alias_documents_its_substituted_value(source: str, expression: str, equivalent: Any) -> None:
    assert body_schema(evaluate(source, expression)) == body_schema(equivalent)


@pytest.mark.parametrize("library", ["dc", "ms", "py"])
def test_generic_type_alias_as_model_field(library: str) -> None:
    alias_property = body_schema(make_model(library, evaluate(PAIR, "Pair[int]")))[1]["Model"]["properties"]["x"]
    assert alias_property == body_schema(make_model(library, tuple[int, int]))[1]["Model"]["properties"]["x"]


def test_generic_type_alias_as_query_parameter() -> None:
    def parameter_schema(annotation: Any) -> dict[str, Any]:
        @get("/")
        async def handler(q: FromQuery[annotation]) -> None:  # pyright: ignore[reportInvalidTypeForm]
            return None

        schema: dict[str, Any] = build_document(handler)["paths"]["/"]["get"]["parameters"][0]["schema"]
        return schema

    assert parameter_schema(evaluate(PAIR, "Pair[int]")) == parameter_schema(tuple[int, int])


def test_unsubscripted_generic_type_alias_is_unchanged() -> None:
    schema, components = body_schema(evaluate(PAIR, "Pair"))
    assert schema["prefixItems"] == [{"type": "object"}, {"type": "object"}]
    assert components == {}


@pytest.mark.parametrize(
    ("source", "expression"),
    [("type Tup[*Ts] = tuple[*Ts]", "Tup[int, str]"), ("type Call[**P] = int", "Call[int, str]")],
    ids=["type-var-tuple", "param-spec"],
)
def test_subscripted_type_alias_with_variadic_or_param_spec_parameter_raises(source: str, expression: str) -> None:
    with pytest.raises(ImproperlyConfiguredException, match="TypeVarTuple or ParamSpec"):
        body_schema(evaluate(source, expression))


JSON = "type JSON = None | bool | str | float | int | list[JSON] | dict[str, JSON]"
TREE = "type Tree = int | list[Tree]"
JSON_REF = {"$ref": "#/components/schemas/JSON"}
TREE_REF = {"$ref": "#/components/schemas/Tree"}
TREE_COMPONENT = {"oneOf": [{"type": "integer"}, {"items": TREE_REF, "type": "array"}]}


@pytest.mark.parametrize(
    ("source", "members"),
    [
        pytest.param(
            JSON,
            [
                {"type": "boolean"},
                {"type": "string"},
                {"type": "number"},
                {"type": "integer"},
                {"items": JSON_REF, "type": "array"},
                {"additionalProperties": JSON_REF, "type": "object"},
                {"type": "null"},
            ],
            id="issue-4843",
        ),
        pytest.param(
            "type JSON = dict[str, JSON] | list[JSON] | str | int | float | bool | None",
            [
                {"additionalProperties": JSON_REF, "type": "object"},
                {"items": JSON_REF, "type": "array"},
                {"type": "string"},
                {"type": "integer"},
                {"type": "number"},
                {"type": "boolean"},
                {"type": "null"},
            ],
            id="containers-first",
        ),
    ],
)
def test_recursive_type_alias(source: str, members: list[dict[str, Any]]) -> None:
    assert body_schema(evaluate(source, "JSON")) == (JSON_REF, {"JSON": {"anyOf": members}})


def test_recursive_type_alias_in_optional_and_annotated() -> None:
    tree = evaluate(TREE, "Tree")
    assert body_schema(Optional[tree]) == ({"oneOf": [TREE_REF, {"type": "null"}]}, {"Tree": TREE_COMPONENT})
    assert body_schema(Annotated[tree, "doc"]) == (TREE_REF, {"Tree": TREE_COMPONENT})


def test_mutually_recursive_type_aliases_are_independent_of_handler_order() -> None:
    namespace: dict[str, Any] = {"__name__": __name__}
    exec("type A = list[B] | int\ntype B = dict[str, A]", namespace)
    handler_a, handler_b = returning("/a", namespace["A"]), returning("/b", namespace["B"])

    schemas = build_document(handler_a, handler_b)["components"]["schemas"]
    assert schemas == {
        "A": {"oneOf": [{"items": {"$ref": "#/components/schemas/B"}, "type": "array"}, {"type": "integer"}]},
        "B": {"additionalProperties": {"$ref": "#/components/schemas/A"}, "type": "object"},
    }
    assert build_document(handler_b, handler_a)["components"]["schemas"] == schemas


def test_recursive_type_alias_of_recursive_type_alias() -> None:
    namespace: dict[str, Any] = {"__name__": __name__}
    exec("type A = B\ntype B = list[A] | int", namespace)
    handler_a, handler_b = returning("/a", namespace["A"]), returning("/b", namespace["B"])

    schemas = build_document(handler_a, handler_b)["components"]["schemas"]
    assert schemas == {
        "A": {"oneOf": [{"$ref": "#/components/schemas/B"}]},
        "B": {"oneOf": [{"items": {"$ref": "#/components/schemas/A"}, "type": "array"}, {"type": "integer"}]},
    }
    assert build_document(handler_b, handler_a)["components"]["schemas"] == schemas


def test_polymorphically_recursive_type_alias_raises() -> None:
    alias = evaluate("type Tree[T] = T | list[Tree[list[T]]]", "Tree[int]")

    with pytest.raises(ImproperlyConfiguredException, match="expands to ever larger types"):
        body_schema(alias)


def test_type_alias_annotating_itself_on_a_pydantic_field_does_not_hang() -> None:
    model = pydantic.create_model(
        "Model", x=(evaluate("type X = Annotated[X, pydantic.Field(ge=0)]", "X"), ...), __module__=__name__
    )

    schema, components = body_schema(model)

    assert schema == {"$ref": "#/components/schemas/Model"}
    assert list(components["Model"]["properties"]) == ["x"]


def test_non_recursive_type_alias_stays_inline() -> None:
    schema, components = body_schema(evaluate(f"{JSON}\ntype Document = dict[str, JSON]", "Document"))
    assert schema == {"additionalProperties": JSON_REF, "type": "object"}
    assert list(components) == ["JSON"]
    assert body_schema(evaluate("type Score = int", "Score")) == ({"type": "integer"}, {})


def test_recursive_generic_type_alias() -> None:
    tree = evaluate("type Tree[T] = T | list[Tree[T]]", "Tree")

    assert build_document(accepting("/a", tree[int]), accepting("/b", tree[str]))["components"]["schemas"] == {
        "Tree_int": {
            "oneOf": [{"type": "integer"}, {"items": {"$ref": "#/components/schemas/Tree_int"}, "type": "array"}]
        },
        "Tree_str": {
            "oneOf": [{"type": "string"}, {"items": {"$ref": "#/components/schemas/Tree_str"}, "type": "array"}]
        },
    }


@pytest.mark.parametrize("library", ["dc", "py"])
def test_recursive_type_alias_as_model_field(library: str) -> None:
    components = body_schema(make_model(library, evaluate(TREE, "Tree")))[1]
    assert components["Model"]["properties"]["x"] == TREE_REF
    assert components["Tree"] == TREE_COMPONENT


@pytest.mark.parametrize("library", ["alias", "py"])
def test_recursive_type_alias_with_generated_examples(library: str) -> None:
    tree = evaluate(TREE, "Tree")
    annotation = tree if library == "alias" else make_model(library, tree)

    schema, components = body_schema(annotation, create_examples=True)

    assert components["Tree"]["oneOf"] == TREE_COMPONENT["oneOf"]
    assert schema == TREE_REF or components["Model"]["properties"]["x"]["$ref"] == TREE_REF["$ref"]


def test_recursive_type_alias_usage_with_metadata_is_wrapped_in_one_of() -> None:
    model = pydantic.create_model("Model", x=(evaluate(TREE, "Tree"), pydantic.Field(description="a tree")))

    components = body_schema(model)[1]

    assert components["Model"]["properties"]["x"] == {"oneOf": [TREE_REF], "description": "a tree"}
    assert components["Tree"] == TREE_COMPONENT


def test_same_named_recursive_type_aliases_and_models_get_distinct_components() -> None:
    model = dataclasses.make_dataclass("Tree", [("value", int)])
    model.__module__ = __name__
    handlers = (
        accepting("/first", evaluate(TREE, "Tree")),
        accepting("/second", evaluate("type Tree = str | list[Tree]", "Tree")),
        accepting("/model", model),
    )

    document = build_document(*handlers)

    assert list(document["components"]["schemas"]) == ["Tree", "Tree_2", "Tree_3"]
    assert {
        path: item["post"]["requestBody"]["content"]["application/json"]["schema"]
        for path, item in document["paths"].items()
    } == {
        "/first": TREE_REF,
        "/second": {"$ref": "#/components/schemas/Tree_2"},
        "/model": {"$ref": "#/components/schemas/Tree_3"},
    }


def test_recursive_type_alias_is_served_as_documented() -> None:
    tree = evaluate(TREE, "Tree")
    handlers = [accepting("/create", make_model("py", tree)), returning("/read", tree, [1, [2, [3]]])]

    with create_test_client(handlers) as client:
        document = client.app.openapi_schema.to_schema()
        assert document["components"]["schemas"]["Tree"] == TREE_COMPONENT
        assert (
            document["paths"]["/read"]["get"]["responses"]["200"]["content"]["application/json"]["schema"] == TREE_REF
        )
        assert client.post("/create", json={"x": [1, [2, [3]]]}).status_code == 201
        assert client.post("/create", json={"x": ["a"]}).status_code == 400
        assert client.get("/read").json() == [1, [2, [3]]]


def test_type_alias_constraint_precedence_on_parameters() -> None:
    def build(limit: Any) -> HTTPRouteHandler:
        @get("/")
        async def handler(
            extended: Annotated[limit, QueryParameter(le=10)],  # pyright: ignore[reportInvalidTypeForm]
            overridden: Annotated[limit, QueryParameter(ge=5)],  # pyright: ignore[reportInvalidTypeForm]
        ) -> None:
            return None

        return handler

    with create_test_client([build(evaluate("type Limit = Annotated[int, annotated_types.Ge(0)]", "Limit"))]) as client:
        parameters = client.app.openapi_schema.to_schema()["paths"]["/"]["get"]["parameters"]
        schemas = {parameter["name"]: parameter["schema"] for parameter in parameters}
        assert schemas["extended"]["maximum"] == 10
        assert schemas["overridden"]["minimum"] == 5
        assert client.get("/", params={"extended": 11, "overridden": 7}).status_code == 400
        assert client.get("/", params={"extended": 1, "overridden": 3}).status_code == 400
        assert client.get("/", params={"extended": 1, "overridden": 7}).status_code == 200
