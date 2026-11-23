import dataclasses
from collections.abc import Callable, Mapping
from types import GenericAlias
from typing import Annotated, Any, Final, Literal

from litestar import Response
from litestar.dto import DTOField
from tests.unit.test_dto.conformance.models import (
    PRIVATE,
    READ_ONLY,
    WRITE_ONLY,
    Envelope,
    F,
    Factory,
    Library,
    Maker,
    Page,
)

Direction = Literal["in", "out"]
DIRECTIONS: Final[tuple[Direction, ...]] = ("in", "out")


@dataclasses.dataclass(frozen=True)
class NA:
    reason: str


@dataclasses.dataclass(frozen=True)
class Req:
    label: str
    body: Any
    status: int
    received: Any = None


@dataclasses.dataclass(frozen=True)
class Case:
    model: Any
    instance: Callable[[], Any]
    annotation: Any = None


@dataclasses.dataclass(frozen=True)
class Feature:
    id: str
    build: Callable[[Maker], Case]
    requests: tuple[Req, ...] | NA
    response: Any
    config: Mapping[str, Any] = dataclasses.field(default_factory=dict)
    dto_data: bool = False
    receive: Callable[[Any], Any] | None = None
    na: Mapping[Library, str] = dataclasses.field(default_factory=dict)
    accessor: Callable[[object, str], Any] | None = None


FEATURES: Final[list[Feature]] = []


def feature(
    feature_id: str,
    build: Callable[[Maker], Case],
    *,
    requests: tuple[Req, ...] | NA,
    response: Any,
    config: Mapping[str, Any] | None = None,
    dto_data: bool = False,
    receive: Callable[[Any], Any] | None = None,
    na: Mapping[Library, str] | None = None,
    accessor: Callable[[object, str], Any] | None = None,
) -> None:
    FEATURES.append(Feature(feature_id, build, requests, response, config or {}, dto_data, receive, na or {}, accessor))


def model(name: str, /, **fields: Any) -> dict[str, Any]:
    return {"$model": name, **fields}


def _user(m: Maker) -> Case:
    user = m.model("User", F("name", str), F("age", int, 0))
    return Case(user, lambda: user(name="a", age=1))


def _child(m: Maker) -> Any:
    return m.model("Child", F("label", str), F("secret", str, "s"), frozen=True)


def _parent(m: Maker) -> Case:
    child = _child(m)
    parent = m.model("Parent", F("name", str), F("child", child))
    return Case(parent, lambda: parent(name="a", child=child(label="l", secret="x")))


def _parent_of_many(m: Maker) -> Case:
    child = _child(m)
    parent = m.model("Parent", F("name", str), F("children", GenericAlias(list, child)))
    return Case(parent, lambda: parent(name="a", children=[child(label="l", secret="x")]))


_NO_UNDERSCORE: Final = "pydantic treats underscore attributes as private attributes, not fields"

feature(
    "plain",
    _user,
    requests=(
        Req("valid", {"name": "a", "age": 1}, 201, model("User", name="a", age=1)),
        Req("omit_default", {"name": "a"}, 201, model("User", name="a", age=0)),
        Req("unknown_field", {"name": "a", "zzz": 1}, 201, model("User", name="a", age=0)),
        Req("missing_required", {"age": 1}, 400),
        Req("wrong_type", {"name": 1}, 400),
    ),
    response={"name": "a", "age": 1},
)
feature(
    "exclude",
    _user,
    config={"exclude": {"age"}},
    requests=(
        Req("valid", {"name": "a"}, 201, model("User", name="a", age=0)),
        Req("excluded_sent", {"name": "a", "age": 5}, 201, model("User", name="a", age=0)),
    ),
    response={"name": "a"},
)
feature(
    "exclude_nested",
    _parent,
    config={"exclude": {"child.secret"}},
    requests=(
        Req(
            "excluded_sent",
            {"name": "a", "child": {"label": "l", "secret": "x"}},
            201,
            model("Parent", name="a", child=model("Child", label="l", secret="s")),
        ),
    ),
    response={"name": "a", "child": {"label": "l"}},
)
feature(
    "exclude_list_item",
    _parent_of_many,
    config={"exclude": {"children.0.secret"}},
    requests=(
        Req(
            "excluded_sent",
            {"name": "a", "children": [{"label": "l", "secret": "x"}]},
            201,
            model("Parent", name="a", children=[model("Child", label="l", secret="s")]),
        ),
    ),
    response={"name": "a", "children": [{"label": "l"}]},
)
feature(
    "include",
    _user,
    config={"include": {"name"}},
    requests=(
        Req("valid", {"name": "a"}, 201, model("User", name="a", age=0)),
        Req("not_included_sent", {"name": "a", "age": 5}, 201, model("User", name="a", age=0)),
    ),
    response={"name": "a"},
)
feature(
    "include_nested",
    _parent,
    config={"include": {"name", "child.label"}},
    requests=(
        Req(
            "not_included_sent",
            {"name": "a", "child": {"label": "l", "secret": "x"}},
            201,
            model("Parent", name="a", child=model("Child", label="l", secret="s")),
        ),
    ),
    response={"name": "a", "child": {"label": "l"}},
)
feature(
    "rename_fields",
    _user,
    config={"rename_fields": {"name": "userName"}},
    requests=(
        Req("by_alias", {"userName": "a", "age": 1}, 201, model("User", name="a", age=1)),
        Req("by_name", {"name": "a", "age": 1}, 400),
    ),
    response={"userName": "a", "age": 1},
)
feature(
    "rename_fields_nested",
    _parent,
    config={"rename_fields": {"child.label": "tag"}},
    requests=(
        Req(
            "by_alias",
            {"name": "a", "child": {"tag": "l"}},
            201,
            model("Parent", name="a", child=model("Child", label="l", secret="s")),
        ),
        Req("by_name", {"name": "a", "child": {"label": "l"}}, 400),
    ),
    response={"name": "a", "child": {"tag": "l", "secret": "x"}},
)


def _snake(m: Maker) -> Case:
    inner = m.model("Inner", F("inner_label", str))
    outer = m.model("Outer", F("first_name", str), F("inner_item", inner))
    return Case(outer, lambda: outer(first_name="a", inner_item=inner(inner_label="l")))


_SNAKE_RECEIVED: Final = model("Outer", first_name="a", inner_item=model("Inner", inner_label="l"))

feature(
    "rename_strategy_camel",
    _snake,
    config={"rename_strategy": "camel"},
    requests=(
        Req("by_alias", {"firstName": "a", "innerItem": {"innerLabel": "l"}}, 201, _SNAKE_RECEIVED),
        Req("by_name", {"first_name": "a", "inner_item": {"inner_label": "l"}}, 400),
    ),
    response={"firstName": "a", "innerItem": {"innerLabel": "l"}},
)
feature(
    "rename_strategy_upper",
    _snake,
    config={"rename_strategy": "upper"},
    requests=(Req("by_alias", {"FIRST_NAME": "a", "INNER_ITEM": {"INNER_LABEL": "l"}}, 201, _SNAKE_RECEIVED),),
    response={"FIRST_NAME": "a", "INNER_ITEM": {"INNER_LABEL": "l"}},
)
feature(
    "rename_strategy_lower",
    _snake,
    config={"rename_strategy": "lower"},
    requests=(Req("by_alias", {"first_name": "a", "inner_item": {"inner_label": "l"}}, 201, _SNAKE_RECEIVED),),
    response={"first_name": "a", "inner_item": {"inner_label": "l"}},
)
feature(
    "rename_strategy_pascal",
    _snake,
    config={"rename_strategy": "pascal"},
    requests=(
        Req("by_alias", {"FirstName": "a", "InnerItem": {"InnerLabel": "l"}}, 201, _SNAKE_RECEIVED),
        Req("by_name", {"first_name": "a", "inner_item": {"inner_label": "l"}}, 400),
    ),
    response={"FirstName": "a", "InnerItem": {"InnerLabel": "l"}},
)
feature(
    "rename_strategy_kebab",
    _snake,
    config={"rename_strategy": "kebab"},
    requests=(
        Req("by_alias", {"first-name": "a", "inner-item": {"inner-label": "l"}}, 201, _SNAKE_RECEIVED),
        Req("by_name", {"first_name": "a", "inner_item": {"inner_label": "l"}}, 400),
    ),
    response={"first-name": "a", "inner-item": {"inner-label": "l"}},
)


def _prefix(name: str) -> str:
    return f"x-{name}"


feature(
    "rename_strategy_callable",
    _snake,
    config={"rename_strategy": _prefix},
    requests=(Req("by_alias", {"x-first_name": "a", "x-inner_item": {"x-inner_label": "l"}}, 201, _SNAKE_RECEIVED),),
    response={"x-first_name": "a", "x-inner_item": {"x-inner_label": "l"}},
)
feature(
    "rename_fields_over_strategy",
    _snake,
    config={"rename_strategy": "camel", "rename_fields": {"first_name": "given"}},
    requests=(Req("by_alias", {"given": "a", "innerItem": {"innerLabel": "l"}}, 201, _SNAKE_RECEIVED),),
    response={"given": "a", "innerItem": {"innerLabel": "l"}},
)


def _chain(m: Maker) -> Case:
    level3 = m.model("Level3", F("name", str, "d3"))
    level2 = m.model("Level2", F("name", str, "d2"), F("down", level3, Factory(level3)))
    level1 = m.model("Level1", F("name", str, "d1"), F("down", level2, Factory(level2)))
    root = m.model("Root", F("name", str), F("down", level1, Factory(level1)))
    return Case(root, lambda: root(name="a", down=level1(name="b", down=level2(name="c", down=level3(name="d")))))


_CHAIN_BODY: Final = {"name": "a", "down": {"name": "b", "down": {"name": "c", "down": {"name": "d"}}}}


def _chain_received(*names: str) -> dict[str, Any]:
    level3 = model("Level3", name=names[2])
    level2 = model("Level2", name=names[1], down=level3)
    level1 = model("Level1", name=names[0], down=level2)
    return model("Root", name="a", down=level1)


feature(
    "max_nested_depth_0",
    _chain,
    config={"max_nested_depth": 0},
    requests=(Req("deep", _CHAIN_BODY, 201, _chain_received("d1", "d2", "d3")),),
    response={"name": "a"},
)
feature(
    "max_nested_depth_1",
    _chain,
    requests=(Req("deep", _CHAIN_BODY, 201, _chain_received("b", "d2", "d3")),),
    response={"name": "a", "down": {"name": "b"}},
)
feature(
    "max_nested_depth_2",
    _chain,
    config={"max_nested_depth": 2},
    requests=(Req("deep", _CHAIN_BODY, 201, _chain_received("b", "c", "d3")),),
    response={"name": "a", "down": {"name": "b", "down": {"name": "c"}}},
)


def _builtins(data: Any) -> Any:
    return data.as_builtins()


feature(
    "partial",
    _user,
    config={"partial": True},
    dto_data=True,
    receive=_builtins,
    requests=(
        Req("one_field", {"age": 3}, 201, {"age": 3}),
        Req("empty", {}, 201, {}),
        Req("all_fields", {"name": "a", "age": 3}, 201, {"name": "a", "age": 3}),
        Req("wrong_type", {"age": "x"}, 400),
    ),
    response={"name": "a", "age": 1},
)


def _underscore(m: Maker) -> Case:
    item = m.model("Item", F("name", str), F("_hidden", str, "h"))
    return Case(item, lambda: item(name="a", _hidden="x"))


feature(
    "underscore_fields_private",
    _underscore,
    requests=(Req("sent", {"name": "a", "_hidden": "x"}, 201, model("Item", name="a", _hidden="h")),),
    response={"name": "a"},
    na={"py": _NO_UNDERSCORE},
)
feature(
    "underscore_fields_public",
    _underscore,
    config={"underscore_fields_private": False},
    requests=(Req("sent", {"name": "a", "_hidden": "x"}, 201, model("Item", name="a", _hidden="x")),),
    response={"name": "a", "_hidden": "x"},
    na={"py": _NO_UNDERSCORE},
)
feature(
    "forbid_unknown_fields",
    _user,
    config={"forbid_unknown_fields": True},
    requests=(
        Req("valid", {"name": "a", "age": 1}, 201, model("User", name="a", age=1)),
        Req("unknown_field", {"name": "a", "zzz": 1}, 400),
    ),
    response={"name": "a", "age": 1},
)


def _marked(mark: Any) -> Callable[[Maker], Case]:
    def build(m: Maker) -> Case:
        item = m.model("Item", F("name", str), F("token", Annotated[str, mark], "t"))
        return Case(item, lambda: item(name="a", token="x"))

    return build


feature(
    "mark_private",
    _marked(PRIVATE),
    requests=(Req("sent", {"name": "a", "token": "x"}, 201, model("Item", name="a", token="t")),),
    response={"name": "a"},
)
feature(
    "mark_read_only",
    _marked(READ_ONLY),
    requests=(Req("sent", {"name": "a", "token": "x"}, 201, model("Item", name="a", token="t")),),
    response={"name": "a", "token": "x"},
)
feature(
    "mark_write_only",
    _marked(WRITE_ONLY),
    requests=(Req("sent", {"name": "a", "token": "x"}, 201, model("Item", name="a", token="x")),),
    response={"name": "a"},
)

_CHILD_BODY: Final = {"label": "l", "secret": "x"}
_CHILD_RECEIVED: Final = model("Child", label="l", secret="s")
_CHILD_SENT: Final = {"label": "l"}


def _marked_child(m: Maker) -> Any:
    return m.model("Child", F("label", str), F("secret", Annotated[str, PRIVATE], "s"), frozen=True)


def shape(
    feature_id: str,
    annotation_of: Callable[[Any], Any],
    value_of: Callable[[Any], Any],
    *,
    requests: tuple[Req, ...],
    response: Any,
) -> None:
    def build(m: Maker) -> Case:
        child = _marked_child(m)
        holder = m.model("Holder", F("value", annotation_of(child)))
        return Case(holder, lambda: holder(value=value_of(child(label="l", secret="x"))))

    feature(feature_id, build, requests=requests, response=response)


def _holder(value: Any) -> dict[str, Any]:
    return model("Holder", value=value)


shape(
    "nested_model",
    lambda child: child,
    lambda child: child,
    requests=(
        Req("valid", {"value": _CHILD_BODY}, 201, _holder(_CHILD_RECEIVED)),
        Req("bad_nested", {"value": {"label": 1}}, 400),
    ),
    response={"value": _CHILD_SENT},
)
shape(
    "list_of_models",
    lambda child: GenericAlias(list, child),
    lambda child: [child],
    requests=(
        Req("valid", {"value": [_CHILD_BODY]}, 201, _holder([_CHILD_RECEIVED])),
        Req("bad_item", {"value": [{"label": 1}]}, 400),
    ),
    response={"value": [_CHILD_SENT]},
)
shape(
    "set_of_models",
    lambda child: GenericAlias(set, child),
    lambda child: {child},
    requests=(Req("valid", {"value": [_CHILD_BODY]}, 201, _holder([_CHILD_RECEIVED])),),
    response={"value": [_CHILD_SENT]},
)
shape(
    "dict_of_models",
    lambda child: GenericAlias(dict, (str, child)),
    lambda child: {"k": child},
    requests=(
        Req("valid", {"value": {"k": _CHILD_BODY}}, 201, _holder({"k": _CHILD_RECEIVED})),
        Req("bad_value", {"value": {"k": {"label": 1}}}, 400),
    ),
    response={"value": {"k": _CHILD_SENT}},
)
shape(
    "tuple_fixed",
    lambda child: GenericAlias(tuple, (child, int)),
    lambda child: (child, 1),
    requests=(
        Req("valid", {"value": [_CHILD_BODY, 1]}, 201, _holder([_CHILD_RECEIVED, 1])),
        Req("too_short", {"value": [_CHILD_BODY]}, 400),
    ),
    response={"value": [_CHILD_SENT, 1]},
)
shape(
    "tuple_variable",
    lambda child: GenericAlias(tuple, (child, ...)),
    lambda child: (child, child),
    requests=(
        Req("valid", {"value": [_CHILD_BODY, _CHILD_BODY]}, 201, _holder([_CHILD_RECEIVED, _CHILD_RECEIVED])),
        Req("empty", {"value": []}, 201, _holder([])),
    ),
    response={"value": [_CHILD_SENT, _CHILD_SENT]},
)
shape(
    "optional_model",
    lambda child: child | None,
    lambda child: child,
    requests=(
        Req("model", {"value": _CHILD_BODY}, 201, _holder(_CHILD_RECEIVED)),
        Req("null", {"value": None}, 201, _holder(None)),
    ),
    response={"value": _CHILD_SENT},
)
shape(
    "union_model_scalar",
    lambda child: child | int,
    lambda child: child,
    requests=(
        Req("model", {"value": _CHILD_BODY}, 201, _holder(_CHILD_RECEIVED)),
        Req("scalar", {"value": 3}, 201, _holder(3)),
        Req("neither", {"value": "x"}, 400),
    ),
    response={"value": _CHILD_SENT},
)


def _root_list(m: Maker) -> Case:
    user = m.model("User", F("name", str), F("age", int, 0))
    return Case(user, lambda: [user(name="a", age=1), user(name="b", age=2)], GenericAlias(list, user))


feature(
    "root_list",
    _root_list,
    config={"exclude": {"age"}},
    requests=(
        Req(
            "valid",
            [{"name": "a", "age": 5}, {"name": "b"}],
            201,
            [model("User", name="a", age=0), model("User", name="b", age=0)],
        ),
        Req("not_list", {"name": "a"}, 400),
    ),
    response=[{"name": "a"}, {"name": "b"}],
)


def constraint(
    feature_id: str, annotation_of: Callable[[Maker], Any], valid: Any, invalid: Any, *, extra: tuple[Req, ...] = ()
) -> None:
    def build(m: Maker) -> Case:
        holder = m.model("Holder", F("value", annotation_of(m)))
        return Case(holder, lambda: holder(value=valid))

    feature(
        feature_id,
        build,
        requests=(Req("valid", {"value": valid}, 201, _holder(valid)), Req("invalid", {"value": invalid}, 400), *extra),
        response={"value": valid},
    )


constraint("constraint_number", lambda m: m.constrained(int, ge=1), 1, 0)
constraint("constraint_string", lambda m: m.constrained(str, min_length=3, pattern="^a"), "abc", "ab")
constraint("constraint_collection", lambda m: m.constrained(list[int], min_length=1), [1], [])
constraint("constraint_list_item", lambda m: GenericAlias(list, m.constrained(str, min_length=3)), ["abc"], ["ab"])
constraint("constraint_dict_value", lambda m: GenericAlias(dict, (str, m.constrained(int, ge=1))), {"k": 1}, {"k": 0})
constraint("constraint_union_arm", lambda m: m.constrained(str, min_length=3) | int, "abc", "ab")
constraint(
    "constraint_optional",
    lambda m: m.constrained(str, pattern="^a") | None,
    "abc",
    "b",
    extra=(Req("null", {"value": None}, 201, _holder(None)),),
)


def _partial_constraint(annotation_of: Callable[[Maker], Any], valid: Any) -> Callable[[Maker], Case]:
    def build(m: Maker) -> Case:
        holder = m.model("Holder", F("value", annotation_of(m)), F("other", int, 0))
        return Case(holder, lambda: holder(value=valid))

    return build


feature(
    "constraint_partial_length",
    _partial_constraint(lambda m: m.constrained(str, min_length=3), "abc"),
    config={"partial": True},
    dto_data=True,
    receive=_builtins,
    requests=(
        Req("valid", {"value": "abc"}, 201, {"value": "abc"}),
        Req("unset", {"other": 1}, 201, {"other": 1}),
        Req("invalid", {"value": "ab"}, 400),
    ),
    response={"value": "abc", "other": 0},
)
feature(
    "constraint_partial_number",
    _partial_constraint(lambda m: m.constrained(int, ge=1), 1),
    config={"partial": True},
    dto_data=True,
    receive=_builtins,
    requests=(
        Req("valid", {"value": 1}, 201, {"value": 1}),
        Req("unset", {"other": 1}, 201, {"other": 1}),
        Req("invalid", {"value": 0}, 400),
    ),
    response={"value": 1, "other": 0},
)


_envelope_type: Any = Envelope
_page_type: Any = Page
_response_type: Any = Response


def _envelope(m: Maker) -> Case:
    user = m.model("User", F("name", str), F("age", int, 0))
    return Case(user, lambda: Envelope(data=user(name="a", age=1), count=1), _envelope_type[user])


def _page(m: Maker) -> Case:
    user = m.model("User", F("name", str), F("age", int, 0))
    return Case(user, lambda: Page(items=[user(name="a", age=1)], total=1), _page_type[user])


def _response(m: Maker) -> Case:
    user = m.model("User", F("name", str), F("age", int, 0))
    return Case(user, lambda: Response(user(name="a", age=1)), _response_type[user])


_RETURN_SIDE: Final = NA("generic wrappers are resolved for return annotations only")

feature(
    "generic_wrapper",
    _envelope,
    config={"exclude": {"age"}},
    requests=_RETURN_SIDE,
    response={"data": {"name": "a"}, "count": 1},
)
feature(
    "generic_wrapper_list",
    _page,
    config={"exclude": {"age"}},
    requests=_RETURN_SIDE,
    response={"items": [{"name": "a"}], "total": 1},
)
feature(
    "response_wrapper",
    _response,
    config={"exclude": {"age"}},
    requests=NA("Response[T] is a return annotation"),
    response={"name": "a"},
)


def _create_instance(data: Any) -> Any:
    return data.create_instance(age=7)


feature(
    "dto_data",
    _user,
    config={"exclude": {"age"}},
    dto_data=True,
    receive=_create_instance,
    requests=(
        Req("valid", {"name": "a"}, 201, model("User", name="a", age=7)),
        Req("excluded_sent", {"name": "a", "age": 5}, 201, model("User", name="a", age=7)),
        Req("missing_required", {}, 400),
    ),
    response=NA("DTOData is a request annotation"),
)


def _literal_mark(m: Maker) -> Case:
    item = m.model("Item", F("name", str), F("token", Annotated[str, DTOField(mark="private")], "t"))
    return Case(item, lambda: item(name="a", token="x"))


feature(
    "mark_private_literal",
    _literal_mark,
    requests=(Req("sent", {"name": "a", "token": "x"}, 201, model("Item", name="a", token="t")),),
    response={"name": "a"},
)


def _with_property(m: Maker) -> Case:
    return Case(m.shout, lambda: m.shout(name="a"))


feature(
    "property_read_only",
    _with_property,
    requests=(
        Req("valid", {"name": "a"}, 201, model("Shout", name="a")),
        Req("property_sent", {"name": "a", "loud": "X"}, 201, model("Shout", name="a")),
    ),
    response={"name": "a", "loud": "A"},
    na={"py": "pydantic properties are not model fields"},
)


def _link_only(m: Maker) -> Case:
    leaf = m.model("Leaf", F("first", str), F("second", str))
    link = m.model("Link", F("leaf", leaf))
    root = m.model("Root", F("name", str), F("link", link))
    return Case(root, lambda: root(name="a", link=link(leaf=leaf(first="f", second="s"))))


feature(
    "nested_link_only_intermediate",
    _link_only,
    config={"max_nested_depth": 2},
    requests=(
        Req(
            "valid",
            {"name": "a", "link": {"leaf": {"first": "f", "second": "s"}}},
            201,
            model("Root", name="a", link=model("Link", leaf=model("Leaf", first="f", second="s"))),
        ),
    ),
    response={"name": "a", "link": {"leaf": {"first": "f", "second": "s"}}},
)


def _non_word(m: Maker) -> Case:
    leaf = m.model("Leaf", F("first", str), F("second", str))
    root = m.model("Root", F("name", str), F("a\u00b7b", leaf))
    return Case(root, lambda: root(**{"name": "a", "a\u00b7b": leaf(first="f", second="s")}))


feature(
    "nested_non_word_field_name",
    _non_word,
    requests=(
        Req(
            "valid",
            {"name": "a", "a\u00b7b": {"first": "f", "second": "s"}},
            201,
            model("Root", **{"name": "a", "a\u00b7b": model("Leaf", first="f", second="s")}),
        ),
    ),
    response={"name": "a", "a\u00b7b": {"first": "f", "second": "s"}},
)
shape(
    "optional_list_of_models",
    lambda child: GenericAlias(list, child) | None,
    lambda child: [child],
    requests=(
        Req("models", {"value": [_CHILD_BODY]}, 201, _holder([_CHILD_RECEIVED])),
        Req("null", {"value": None}, 201, _holder(None)),
    ),
    response={"value": [_CHILD_SENT]},
)
shape(
    "list_of_lists_of_models",
    lambda child: GenericAlias(list, GenericAlias(list, child)),
    lambda child: [[child]],
    requests=(Req("valid", {"value": [[_CHILD_BODY]]}, 201, _holder([[_CHILD_RECEIVED]])),),
    response={"value": [[_CHILD_SENT]]},
)


def _tuple_rename(m: Maker) -> Case:
    inner = m.model("Inner", F("inner_label", str))
    outer = m.model("Outer", F("pair_value", GenericAlias(tuple, (inner, int))))
    return Case(outer, lambda: outer(pair_value=(inner(inner_label="l"), 1)))


feature(
    "tuple_fixed_rename_strategy",
    _tuple_rename,
    config={"rename_strategy": "camel"},
    requests=(
        Req(
            "by_alias",
            {"pairValue": [{"innerLabel": "l"}, 1]},
            201,
            model("Outer", pair_value=[model("Inner", inner_label="l"), 1]),
        ),
    ),
    response={"pairValue": [{"innerLabel": "l"}, 1]},
)


def _partial_children(m: Maker) -> Case:
    child = m.model("Child", F("label", str), F("size", int, 0))
    parent = m.model("Parent", F("name", str), F("children", GenericAlias(list, child), Factory(list)))
    return Case(parent, lambda: parent(name="a", children=[child(label="l", size=1)]))


feature(
    "partial_nested_list",
    _partial_children,
    config={"partial": True},
    dto_data=True,
    receive=_builtins,
    requests=(
        Req("full_item", {"children": [{"label": "l", "size": 1}]}, 201, {"children": [{"label": "l", "size": 1}]}),
        Req("partial_item", {"children": [{"size": 1}]}, 201, {"children": [{"size": 1}]}),
    ),
    response={"name": "a", "children": [{"label": "l", "size": 1}]},
)


def _tree(m: Maker) -> Case:
    return Case(m.node, lambda: m.node(name="a", children=[m.node(name="b", children=[m.node(name="c")])]))


feature(
    "self_referential",
    _tree,
    requests=(
        Req(
            "deep",
            {"name": "a", "children": [{"name": "b", "children": [{"name": "c"}]}]},
            201,
            model("Node", name="a", children=[model("Node", name="b", children=[])]),
        ),
    ),
    response={"name": "a", "children": [{"name": "b"}]},
)


def _two_hops(m: Maker) -> Case:
    leaf = m.model("Leaf", F("first", str), F("second", str))
    middle = m.model("Middle", F("label", str), F("leaf", leaf))
    root = m.model("Root", F("name", str), F("middle", middle))
    return Case(root, lambda: root(name="a", middle=middle(label="m", leaf=leaf(first="f", second="s"))))


def _accessor(instance: object, name: str) -> Any:
    return getattr(instance, name)


feature(
    "nested_custom_accessor",
    _two_hops,
    config={"max_nested_depth": 2},
    accessor=_accessor,
    requests=(
        Req(
            "valid",
            {"name": "a", "middle": {"label": "m", "leaf": {"first": "f", "second": "s"}}},
            201,
            model("Root", name="a", middle=model("Middle", label="m", leaf=model("Leaf", first="f", second="s"))),
        ),
    ),
    response={"name": "a", "middle": {"label": "m", "leaf": {"first": "f", "second": "s"}}},
)

_NO_SUCH_NAME: Final = "dataclasses cannot declare this field name"


def _named(*names: str) -> Callable[[Maker], Case]:
    def build(m: Maker) -> Case:
        item = m.model("Item", *(F(name, int) for name in names))
        return Case(item, lambda: item(**{name: index for index, name in enumerate(names, 1)}))

    return build


def field_names(feature_id: str, *names: str) -> None:
    body = {name: index for index, name in enumerate(names, 1)}
    feature(
        feature_id,
        _named(*names),
        requests=(Req("valid", body, 201, model("Item", **body)),),
        response=body,
        na={"dc": _NO_SUCH_NAME},
    )


field_names("field_name_keyword", "size", "class")
field_names("field_names_nfkc_pair", "\u00b5", "\u03bc")
field_names("field_name_nfkc_unstable", "size", "\ufb01eld")
