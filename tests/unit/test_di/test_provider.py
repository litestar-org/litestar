# pyright: reportUnnecessaryTypeIgnoreComment=false
import asyncio
import functools
import inspect
import sys
import threading
from collections.abc import AsyncGenerator, AsyncIterator
from typing import Annotated, Any, Optional, get_args

import pytest

from litestar import Litestar, Request, WebSocket
from litestar.connection import ASGIConnection
from litestar.datastructures import Headers, ImmutableState, State
from litestar.di import (
    Dependency,
    InjectionParameter,
    InjectionTarget,
    NamedDependency,
    Provider,
    ProviderKind,
    TypeDependency,
    _helpers,
    provide,
)
from litestar.di.context import _CleanupStack
from litestar.di.exceptions import DIRegistrationError, DIResolutionError
from litestar.enums import ParamType
from litestar.params import (
    Body,
    FromCookie,
    FromHeader,
    FromPath,
    FromQuery,
    HeaderParameter,
    JSONBody,
    MultipartBody,
    QueryParameter,
    QueryParams,
    RawBody,
    RequestCookies,
)
from litestar.types import Scope
from litestar.utils.signature import ParsedSignature, get_fn_type_hints


class Config:
    pass


class Database:
    pass


async def make_database() -> Database:
    return Database()


class DatabaseFactory:
    async def __call__(self) -> Database:
        return Database()


async def make_marked_database(*, marker: str) -> Database:
    assert marker == "x"
    return Database()


@pytest.mark.parametrize(
    "factory",
    [
        pytest.param(make_database, id="async-function"),
        pytest.param(DatabaseFactory(), id="callable-instance"),
        pytest.param(functools.partial(make_marked_database, marker="x"), id="partial"),
        pytest.param(Database, id="class"),
    ],
)
async def test_provider_produces_callable_return_value(factory: Any) -> None:
    provider = Provider(factory, kind="named", key="db")
    assert isinstance(await provider._produce({}, _CleanupStack()), Database)


async def test_sync_callable_provider_runs_in_thread() -> None:
    def factory() -> int:
        return threading.get_ident()

    provider = Provider(factory, kind="named", sync_to_thread=True)

    assert await provider._produce({}, _CleanupStack()) != threading.get_ident()


async def test_async_generator_provider_cleanup_runs_on_stack_close() -> None:
    events: list[str] = []

    async def factory() -> AsyncGenerator[Database, None]:
        events.append("enter")
        yield Database()
        events.append("exit")

    provider = Provider(factory, kind="named")

    stack = _CleanupStack()
    value = await provider._produce({}, stack)
    assert isinstance(value, Database)
    assert events == ["enter"]

    await stack.aclose()
    assert events == ["enter", "exit"]


def test_class_is_own_type_key() -> None:
    # not its ``__init__``'s return annotation, which is None
    assert Provider(Database, kind="type").key is Database


async def test_async_generator_callable_instance_provider() -> None:
    events: list[str] = []

    class GenFactory:
        async def __call__(self) -> AsyncGenerator[Database, None]:
            events.append("enter")
            yield Database()
            events.append("exit")

    provider = Provider(GenFactory(), kind="named", key="db")
    stack = _CleanupStack()
    assert isinstance(await provider._produce({}, stack), Database)
    await stack.aclose()
    assert events == ["enter", "exit"]


def sync_generator() -> Any:
    yield Database()


class SyncGeneratorFactory:
    def __call__(self) -> Any:
        yield Database()


@pytest.mark.parametrize(
    "factory",
    [pytest.param(sync_generator, id="function"), pytest.param(SyncGeneratorFactory(), id="callable-instance")],
)
def test_sync_generator_raises(factory: Any) -> None:
    with pytest.raises(DIRegistrationError, match="sync generator function is not supported as a provider factory"):
        Provider(factory, kind="named", key="db")


@pytest.mark.parametrize(
    ("key", "kind", "message"),
    [
        pytest.param("db", "type", "String key does not match specified kind 'type'", id="string-key-with-type-kind"),
        pytest.param(
            Database, "named", "Type key does not match specified kind 'named'", id="type-key-with-named-kind"
        ),
    ],
)
def test_key_contradicting_kind_raises(key: Any, kind: Any, message: str) -> None:
    async def factory() -> Database:
        return Database()

    with pytest.raises(DIRegistrationError, match=message):
        Provider(factory, kind=kind, key=key)


def test_unknown_kind_raises() -> None:
    async def factory() -> Database:
        return Database()

    with pytest.raises(
        DIRegistrationError, match=r"Provider .*factory .*: Unknown kind 'name', expected one of 'named', 'type'$"
    ):
        Provider(factory, kind="name")  # type: ignore[arg-type]


def test_named_dependency_uses_parameter_name_as_key() -> None:
    async def factory(db: NamedDependency[Database]) -> Config:
        return Config()

    provider = Provider(factory, kind="type")
    assert provider.dependencies == (InjectionParameter(parameter_name="db", key="db", kind=ProviderKind.NAMED),)


def test_type_dependency_uses_annotated_type_as_key() -> None:
    async def factory(anything: TypeDependency[Database]) -> Config:
        return Config()

    provider = Provider(factory, kind="type")
    assert provider.dependencies == (
        InjectionParameter(parameter_name="anything", key=Database, kind=ProviderKind.TYPE),
    )


def test_type_dependency_on_generic_alias_is_keyed_by_the_alias() -> None:
    async def factory(databases: TypeDependency[list[Database]]) -> Config:
        return Config()

    provider = Provider(factory, kind="type")
    assert provider.dependencies == (
        InjectionParameter(parameter_name="databases", key=list[Database], kind=ProviderKind.TYPE),
    )


class CustomRequest(Request):
    pass


class CustomState(ImmutableState):
    pass


@pytest.mark.parametrize(
    ("annotation", "key"),
    [
        pytest.param(Request, Request, id="request"),
        pytest.param(Request[Any, Any, State], Request, id="generic-request"),
        pytest.param(CustomRequest, CustomRequest, id="request-subclass"),
        pytest.param(WebSocket, WebSocket, id="websocket"),
        pytest.param(ASGIConnection, ASGIConnection, id="asgi-connection"),
        pytest.param(State, State, id="state"),
        pytest.param(CustomState, CustomState, id="state-subclass"),
        pytest.param(Headers, Headers, id="headers"),
        pytest.param(QueryParams, QueryParams, id="query-params"),
        pytest.param(RequestCookies, RequestCookies, id="request-cookies"),
        pytest.param(Scope, Scope, id="scope"),
        pytest.param(RawBody, RawBody, id="raw-body"),
    ],
)
def test_reserved_request_value_annotation_reads_as_type_dependency(annotation: Any, key: Any) -> None:
    async def factory(value: annotation) -> Config:  # pyright: ignore[reportInvalidTypeForm]
        return Config()

    async def marked_factory(value: TypeDependency[annotation]) -> Config:  # pyright: ignore[reportInvalidTypeForm]
        return Config()

    expected = (InjectionParameter(parameter_name="value", key=key, kind=ProviderKind.TYPE),)
    for fn in (factory, marked_factory):
        assert Provider(fn, kind="type").dependencies == expected
        assert InjectionTarget(fn).dependencies == expected


@pytest.mark.parametrize(
    "annotation",
    [
        pytest.param(dict[str, str], id="other-type"),
        pytest.param(Optional[Request], id="optional-reserved-request-value"),
        pytest.param(Request | WebSocket, id="union-of-connection-classes"),
        pytest.param(Litestar, id="app"),
    ],
)
def test_reserved_name_with_other_annotation_raises(annotation: Any) -> None:
    async def factory(request: annotation) -> Config:  # pyright: ignore[reportInvalidTypeForm]
        return Config()

    with pytest.raises(DIRegistrationError, match="'request'.*is not marked as a dependency"):
        Provider(factory, kind="type").resolve_signature()


@pytest.mark.parametrize(
    ("annotation", "key", "param_type", "name"),
    [
        pytest.param(FromQuery[int], "query:value", ParamType.QUERY, "value", id="query"),
        pytest.param(
            Annotated[int, QueryParameter(name="page-size")],
            "query:page-size",
            ParamType.QUERY,
            "page-size",
            id="named-query",
        ),
        pytest.param(FromHeader[str], "header:value", ParamType.HEADER, "value", id="header"),
        pytest.param(
            Annotated[str, HeaderParameter(name="X-Token")],
            "header:x-token",
            ParamType.HEADER,
            "X-Token",
            id="named-header",
        ),
        pytest.param(FromCookie[str], "cookie:value", ParamType.COOKIE, "value", id="cookie"),
        pytest.param(FromPath[int], "path:value", ParamType.PATH, "value", id="path"),
        pytest.param(JSONBody[dict], "body:", None, "", id="json-body"),
        pytest.param(MultipartBody[dict], "body:", None, "", id="multipart-body"),
        pytest.param(Annotated[dict, Body(title="Payload")], "body:", None, "", id="body"),
    ],
)
def test_parameter_or_body_marker_is_request_parameter(
    annotation: Any, key: str, param_type: ParamType | None, name: str
) -> None:
    async def factory(value: annotation, db: NamedDependency[Database]) -> Config:  # pyright: ignore[reportInvalidTypeForm]
        return Config()

    for subject in (Provider(factory, kind="type"), InjectionTarget(factory)):
        assert subject.dependencies == (
            InjectionParameter(parameter_name="value", key=key, kind=ProviderKind.NAMED),
            InjectionParameter(parameter_name="db", key="db", kind=ProviderKind.NAMED),
        )
        (request_parameter,) = subject.request_parameters
        assert (
            request_parameter.parameter_name,
            request_parameter.key,
            request_parameter.param_type,
            request_parameter.name,
        ) == ("value", key, param_type, name)
        assert request_parameter.field_definition.raw == annotation


def test_parameter_marker_with_default_is_optional_dependency() -> None:
    async def factory(limit: FromQuery[int] = 10) -> Config:
        return Config()

    assert Provider(factory, kind="type").dependencies == (
        InjectionParameter(parameter_name="limit", key="query:limit", kind=ProviderKind.NAMED, optional=True),
    )


@pytest.mark.parametrize(
    "annotation",
    [
        pytest.param(NamedDependency[FromQuery[int]], id="query"),
        pytest.param(Annotated[JSONBody[dict], Dependency("payload")], id="body"),
    ],
)
def test_dependency_marker_with_parameter_or_body_marker_raises(annotation: Any) -> None:
    async def factory(value: annotation) -> Config:  # pyright: ignore[reportInvalidTypeForm]
        return Config()

    with pytest.raises(DIRegistrationError, match="'value'.*is marked as a dependency as well as a"):
        Provider(factory, kind="type").resolve_signature()
    with pytest.raises(DIRegistrationError, match="'value'.*is marked as a dependency as well as a"):
        InjectionTarget(factory)


@pytest.mark.parametrize(
    "annotation",
    [
        pytest.param(Optional[FromQuery[int]], id="query"),
        pytest.param(Optional[JSONBody[dict]], id="body"),
    ],
)
def test_parameter_or_body_marker_on_union_member_raises(annotation: Any) -> None:
    async def factory(value: annotation = None) -> Config:  # pyright: ignore[reportInvalidTypeForm]
        return Config()

    with pytest.raises(DIRegistrationError, match="'value'.*marker on a member of its union annotation"):
        Provider(factory, kind="type").resolve_signature()
    with pytest.raises(DIRegistrationError, match="'value'.*marker on a member of its union annotation"):
        InjectionTarget(factory)


@pytest.mark.parametrize(
    ("annotation", "default"),
    [
        pytest.param(float, 5.0, id="plain"),
        pytest.param(Annotated[int, "unrelated metadata"], 1, id="annotated-without-a-marker"),
        pytest.param(int | None, None, id="optional"),
        pytest.param(Optional[Headers], None, id="optional-reserved-request-value"),
    ],
)
def test_unmarked_parameter_with_default_raises(annotation: Any, default: Any) -> None:
    async def factory(db: NamedDependency[Database], option: annotation = default) -> Config:  # pyright: ignore[reportInvalidTypeForm]
        return Config()

    with pytest.raises(DIRegistrationError, match="'option'.*is not marked as a dependency"):
        Provider(factory, kind="type").resolve_signature()


@pytest.mark.parametrize(
    "annotation",
    [
        pytest.param(str, id="plain"),
        pytest.param(Any, id="any"),
        pytest.param(Annotated[int, "unrelated metadata"], id="annotated-without-a-marker"),
        pytest.param(Annotated[Database, ProviderKind.NAMED], id="bare-provider-kind"),
    ],
)
def test_unmarked_parameter_without_default_raises(annotation: Any) -> None:
    async def factory(dsn: annotation) -> Config:  # pyright: ignore[reportInvalidTypeForm]
        return Config()

    with pytest.raises(DIRegistrationError, match="'dsn'.*is not marked as a dependency"):
        Provider(factory, kind="type").resolve_signature()


def test_unannotated_parameter_raises() -> None:

    async def factory(dsn, retries=3) -> Config:  # type: ignore[no-untyped-def]
        return Config()

    with pytest.raises(DIRegistrationError, match="'dsn' does not have a type annotation"):
        Provider(factory, kind="type").resolve_signature()
    with pytest.raises(DIRegistrationError, match="'dsn' does not have a type annotation"):
        InjectionTarget(factory)


def test_var_args_raise() -> None:
    async def factory(*args: Any) -> Config:
        return Config()

    with pytest.raises(DIRegistrationError, match=r"declares \*args"):
        Provider(factory, kind="type").resolve_signature()


def test_var_kwargs_raise() -> None:
    async def factory(**kwargs: Any) -> Config:
        return Config()

    with pytest.raises(DIRegistrationError, match=r"declares \*\*kwargs"):
        Provider(factory, kind="type").resolve_signature()


@pytest.mark.parametrize(
    "annotation",
    [
        pytest.param(NamedDependency[Database], id="dependency-marker"),
        pytest.param(FromQuery[int], id="parameter-marker"),
        pytest.param(Request, id="reserved-request-value"),
    ],
)
def test_marked_var_args_of_target_raises(annotation: Any) -> None:
    async def handler(*args: annotation) -> None: ...  # pyright: ignore[reportInvalidTypeForm]

    with pytest.raises(
        DIRegistrationError, match=r"Parameter '\*args' of .* is marked as a dependency but is variadic"
    ):
        InjectionTarget(handler)


@pytest.mark.parametrize(
    "annotation",
    [
        pytest.param(NamedDependency[Database], id="dependency-marker"),
        pytest.param(FromQuery[int], id="parameter-marker"),
        pytest.param(Request, id="reserved-request-value"),
    ],
)
def test_marked_var_kwargs_of_target_raises(annotation: Any) -> None:
    async def handler(**kwargs: annotation) -> None: ...  # pyright: ignore[reportInvalidTypeForm]

    with pytest.raises(
        DIRegistrationError, match=r"Parameter '\*\*kwargs' of .* is marked as a dependency but is variadic"
    ):
        InjectionTarget(handler)


@pytest.mark.parametrize(
    "annotation",
    [
        pytest.param(NamedDependency[Database], id="dependency-marker"),
        pytest.param(FromQuery[int], id="parameter-marker"),
        pytest.param(Request, id="reserved-request-value"),
    ],
)
def test_positional_only_dependency_raises(annotation: Any) -> None:
    async def factory(db: annotation, /) -> Config:  # pyright: ignore[reportInvalidTypeForm]
        return Config()

    with pytest.raises(DIRegistrationError, match="positional-only"):
        Provider(factory, kind="type").resolve_signature()


def test_positional_only_unmarked_parameter_with_default_raises() -> None:
    async def factory(flag: int = 1, /) -> Config:
        return Config()

    with pytest.raises(DIRegistrationError, match="'flag'.*is not marked as a dependency"):
        Provider(factory, kind="type").resolve_signature()


@pytest.mark.parametrize(
    "annotation",
    [
        pytest.param(Annotated[Database, Dependency(kind="named"), Dependency(kind="type")], id="two-kinds"),
        pytest.param(Annotated[NamedDependency[Database], Dependency("other")], id="shorthand-and-explicit"),
        pytest.param(Annotated[Database, Dependency("one"), Dependency("two")], id="two-keys"),
    ],
)
def test_multiple_markers_on_parameter_raise(annotation: Any) -> None:
    async def factory(db: annotation) -> Config:  # pyright: ignore[reportInvalidTypeForm]
        return Config()

    with pytest.raises(DIRegistrationError, match="more than one dependency marker"):
        Provider(factory, kind="type").resolve_signature()


def test_unresolvable_annotation_raises() -> None:
    async def factory(db: "DoesNotExist") -> int:  # type: ignore[name-defined]  # noqa: F821
        return 1

    with pytest.raises(DIRegistrationError, match="Cannot inspect the signature.*DoesNotExist"):
        Provider(factory, kind="named").resolve_signature()


def test_quoted_marker_under_future_annotations_resolves() -> None:
    """Quotes plus ``from __future__ import annotations`` stringify an annotation twice; the marker
    is read either way."""
    namespace: dict[str, Any] = {"__name__": __name__}
    exec(
        "from __future__ import annotations\nasync def factory(db: 'NamedDependency[int] | None' = None) -> int: ...\n",
        namespace,
    )

    expected = (InjectionParameter("db", "db", ProviderKind.NAMED, optional=True),)
    assert Provider(namespace["factory"], kind="named").dependencies == expected
    assert InjectionTarget(namespace["factory"]).dependencies == expected


def test_quoted_return_annotation_under_future_annotations_is_type_key() -> None:
    namespace: dict[str, Any] = {"__name__": __name__}
    exec("from __future__ import annotations\nasync def factory() -> 'Database': ...\n", namespace)

    assert Provider(namespace["factory"], kind="type").key is Database


def test_given_signature_is_read_instead_of_the_callables() -> None:
    # 'Settings' and 'Client' are not in the module's namespace, so the annotations can
    # should be resolved through the given signature
    class Settings:
        pass

    class Client:
        pass

    async def factory(settings: "NamedDependency[Settings]") -> "Client":
        raise NotImplementedError

    signature = ParsedSignature.from_fn(factory, {"Settings": Settings, "Client": Client})
    expected = (InjectionParameter("settings", "settings", ProviderKind.NAMED),)

    provider = Provider(factory, kind="type", signature=signature)
    assert provider.key is Client
    assert provider.dependencies == expected
    assert InjectionTarget(factory, signature=signature).dependencies == expected


def test_seed_with_signature_raises() -> None:
    async def factory() -> int:
        return 1

    with pytest.raises(DIRegistrationError, match="Provider seed 'value' is given a signature"):
        Provider(None, key="value", signature=ParsedSignature.from_fn(factory, {}))


@pytest.mark.parametrize(
    "described", [pytest.param("wrapped", id="of-the-wrapped-callable"), pytest.param("partial", id="of-the-partial")]
)
def test_given_signature_of_positional_partial_leaves_out_bound_parameters(described: str) -> None:
    """The signature of the wrapped callable is what litestar parses, as it cannot parse a partial."""

    async def factory(dsn: str, db: NamedDependency[Database], cache: NamedDependency[str]) -> Config:
        return Config()

    bound = functools.partial(factory, "sqlite://", Database())
    signature = (
        ParsedSignature.from_fn(factory, {})
        if described == "wrapped"
        else ParsedSignature.from_signature(inspect.signature(bound), get_fn_type_hints(factory))
    )
    expected = (InjectionParameter("cache", "cache", ProviderKind.NAMED),)

    assert Provider(bound, kind="type", signature=signature).dependencies == expected
    assert InjectionTarget(bound, signature=signature).dependencies == expected


def test_given_signature_decides_the_parameters_of_a_class() -> None:
    """The class takes ``**kwargs``, for which a provider raises. The signature describes it the way
    a DIPlugin describes a typed init."""

    class Model:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

    signature = ParsedSignature.from_signature(
        inspect.Signature(
            [
                inspect.Parameter("db", inspect.Parameter.KEYWORD_ONLY),
                inspect.Parameter("label", inspect.Parameter.KEYWORD_ONLY, default="model"),
            ]
        ),
        {"db": NamedDependency[Database], "label": NamedDependency[str]},
    )
    provider = Provider(Model, kind="type", signature=signature)

    assert provider.key is Model
    assert provider.dependencies == (
        InjectionParameter("db", "db", ProviderKind.NAMED),
        InjectionParameter("label", "label", ProviderKind.NAMED, optional=True),
    )


def test_signature_given_at_resolution_is_read_instead_of_the_callables() -> None:
    # 'Settings' and 'Client' are not in the module's namespace, so the annotations can
    # only be resolved through the given signature
    class Settings:
        pass

    class Client:
        pass

    async def factory(settings: "NamedDependency[Settings]") -> "Client":
        raise NotImplementedError

    provider = Provider(factory, kind="type")
    provider.resolve_signature(signature=ParsedSignature.from_fn(factory, {"Settings": Settings, "Client": Client}))

    assert provider.key is Client
    assert provider.dependencies == (InjectionParameter("settings", "settings", ProviderKind.NAMED),)


def test_signature_given_at_construction_is_read_over_one_given_at_resolution() -> None:
    class Model:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

    given_at_construction = ParsedSignature.from_signature(
        inspect.Signature([inspect.Parameter("a", inspect.Parameter.KEYWORD_ONLY)]), {"a": NamedDependency[int]}
    )
    given_at_resolution = ParsedSignature.from_signature(
        inspect.Signature([inspect.Parameter("b", inspect.Parameter.KEYWORD_ONLY)]), {"b": NamedDependency[int]}
    )
    provider = Provider(Model, kind="type", signature=given_at_construction)
    provider.resolve_signature(signature=given_at_resolution)

    assert provider.dependencies == (InjectionParameter("a", "a", ProviderKind.NAMED),)


def test_resolved_provider_keeps_its_dependencies_when_given_a_signature() -> None:
    async def factory(a: NamedDependency[int]) -> Config:
        return Config()

    provider = Provider(factory, kind="type")
    provider.resolve_signature()
    provider.resolve_signature(
        signature=ParsedSignature.from_signature(
            inspect.Signature([inspect.Parameter("b", inspect.Parameter.KEYWORD_ONLY)]), {"b": NamedDependency[int]}
        )
    )

    assert provider.dependencies == (InjectionParameter("a", "a", ProviderKind.NAMED),)


def test_class_init_dependencies_are_discovered() -> None:
    class Repo:
        def __init__(self, db: NamedDependency[Database]) -> None:
            self.db = db

    provider = Provider(Repo, kind="type")
    assert provider.key is Repo
    assert provider.dependencies == (InjectionParameter(parameter_name="db", key="db", kind=ProviderKind.NAMED),)


def test_class_without_init_has_no_parameters() -> None:
    provider = Provider(Database, kind="type")
    assert provider.dependencies == ()
    assert provider.non_di_parameters == ()


def test_name_key_inferred_from_function_name() -> None:
    async def db() -> Database:
        return Database()

    assert Provider(db, kind="named").key == "db"


@pytest.mark.parametrize(
    "annotation", [pytest.param(Database, id="plain"), pytest.param(Annotated[Database, "meta"], id="annotated")]
)
def test_type_key_inferred_from_return_annotation(annotation: Any) -> None:
    async def factory() -> annotation:  # pyright: ignore[reportInvalidTypeForm]
        return Database()

    assert Provider(factory, kind="type").key is Database


@pytest.mark.parametrize(
    "annotation",
    [
        pytest.param(AsyncGenerator[Database, None], id="async-generator"),
        pytest.param(AsyncIterator[Database], id="async-iterator"),
    ],
)
def test_type_key_inferred_from_async_generator_annotation(annotation: Any) -> None:
    async def factory() -> annotation:  # pyright: ignore[reportInvalidTypeForm]
        yield Database()

    assert Provider(factory, kind="type").key is Database


def test_type_key_without_return_annotation_raises() -> None:
    async def factory():  # type: ignore[no-untyped-def]
        return Database()

    with pytest.raises(DIRegistrationError, match="Cannot infer a type key for.*it has no return annotation"):
        Provider(factory, kind="type").key


@pytest.mark.parametrize("annotation", [None, True, False, ...])
def test_type_key_inferred_builtin_constant_raises(annotation: Any) -> None:
    async def factory() -> annotation:  # pyright: ignore[reportInvalidTypeForm]
        return None

    with pytest.raises(DIRegistrationError, match="Cannot infer a type key for.* with constant return annotation"):
        Provider(factory, kind="type").key


@pytest.mark.parametrize(
    "annotation",
    [
        Database | None,
        Optional[Database],
        Database | Config,
        Annotated[Database | None, "meta"],
    ],
)
def test_type_key_inferred_union_raises(annotation: Any) -> None:
    async def factory() -> annotation:  # pyright: ignore[reportInvalidTypeForm]
        return Database()

    with pytest.raises(DIRegistrationError, match="Cannot infer a type key for.* with union return annotation"):
        Provider(factory, kind="type").key


@pytest.mark.parametrize(
    "annotation",
    [
        Database | None,
        Optional[Database],
        Database | Config,
        Annotated[Database | None, "meta"],
    ],
)
def test_type_key_inferred_async_generator_yielding_union_raises(annotation: Any) -> None:
    async def factory() -> AsyncGenerator[annotation, None]:  # pyright: ignore[reportInvalidTypeForm]
        yield Database()

    with pytest.raises(DIRegistrationError, match="Cannot infer a type key for.* with union return annotation"):
        Provider(factory, kind="type").key


def test_explicit_type_key_with_union_return_annotation() -> None:
    async def factory() -> Database | None:
        return Database()

    assert Provider(factory, kind="type", key=Database).key is Database


def test_type_key_inferred_async_generator_without_yield_type_raises() -> None:
    async def factory() -> Any:
        yield Database()

    with pytest.raises(DIRegistrationError, match="Cannot infer a type key for async generator provider"):
        Provider(factory, kind="type").key


def test_name_key_of_callable_instance_without_explicit_key_raises() -> None:
    class Factory:
        async def __call__(self) -> Database:
            return Database()

    with pytest.raises(DIRegistrationError, match="Cannot infer a name key"):
        Provider(Factory(), kind="named").key


def test_explicit_key_is_read_without_the_signature() -> None:
    async def factory(dep: NamedDependency["NotDefinedAnywhere"]) -> int:  # type: ignore[name-defined]  # noqa: F821
        return 1

    provider = Provider(factory, key="thing")

    assert provider.key == "thing"
    with pytest.raises(DIRegistrationError, match="Cannot inspect the signature.*NotDefinedAnywhere"):
        provider.resolve_signature()


def test_name_key_is_inferred_without_the_signature() -> None:
    async def thing(dep: NamedDependency["NotDefinedAnywhere"]) -> int:  # type: ignore[name-defined]  # noqa: F821
        return 1

    provider = Provider(thing, kind="named")

    assert provider.key == "thing"
    with pytest.raises(DIRegistrationError, match="Cannot inspect the signature.*NotDefinedAnywhere"):
        provider.resolve_signature()


def test_class_type_key_is_inferred_without_the_signature() -> None:
    class Model:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

    provider = Provider(Model, kind="type")

    assert provider.key is Model
    with pytest.raises(DIRegistrationError, match=r"declares \*\*kwargs"):
        provider.resolve_signature()


def test_type_key_inferred_from_return_annotation_reads_the_signature() -> None:
    async def factory(dep: NamedDependency["NotDefinedAnywhere"]) -> Database:  # type: ignore[name-defined]  # noqa: F821
        return Database()

    with pytest.raises(DIRegistrationError, match="Cannot inspect the signature.*NotDefinedAnywhere"):
        Provider(factory, kind="type").key


def test_resolve_signature_is_idempotent() -> None:
    async def factory(db: NamedDependency[Database]) -> Config:
        return Config()

    provider = Provider(factory, kind="type")
    provider.resolve_signature()
    first = provider.dependencies
    provider.resolve_signature()
    assert provider.dependencies is first


def test_repr_shows_inferred_key_after_key_read() -> None:
    async def factory() -> Database:
        return Database()

    provider = Provider(factory, kind="type", scope="app")
    assert repr(provider) == f"Provider({factory!r}, kind='type', scope='app')"
    provider.key
    assert repr(provider) == f"Provider({factory!r}, kind='type', scope='app', key={Database!r})"


def test_repr_does_not_resolve_signature() -> None:
    async def factory(dep: NamedDependency["NotDefinedAnywhere"]) -> int:  # type: ignore[name-defined]  # noqa: F821
        return 1

    provider = Provider(factory, key="thing")
    assert repr(provider) == f"Provider({factory!r}, kind='named', scope='handler', key='thing')"
    with pytest.raises(DIRegistrationError):
        provider.resolve_signature()


def test_repr_of_sync_callable_shows_sync_to_thread() -> None:
    def factory() -> int:
        return 1

    provider = Provider(factory, key="thing", sync_to_thread=True)
    assert repr(provider) == f"Provider({factory!r}, kind='named', scope='handler', key='thing', sync_to_thread=True)"


def test_repr_truncates_callable_repr() -> None:
    def factory(numbers: list[int]) -> int:
        return len(numbers)

    provider = Provider(functools.partial(factory, list(range(10_000))), key="thing", sync_to_thread=False)
    assert "..." in repr(provider)
    assert len(repr(provider)) < 300


def test_repr_names_subclass() -> None:
    class RouteProvider(Provider):
        pass

    assert repr(RouteProvider.seed("request")) == "RouteProvider.seed('request', scope='handler')"


def test_provide_returns_provider() -> None:
    @provide(scope="request")
    async def db() -> Database:
        return Database()

    assert isinstance(db, Provider)
    assert db.scope == "request"
    assert db.kind is ProviderKind.NAMED
    assert db.key == "db"


def test_provide_with_type_kind() -> None:
    @provide(scope="app", kind="type")
    async def factory() -> Database:
        return Database()

    assert factory.key is Database
    assert factory.scope == "app"


def test_provide_with_explicit_key() -> None:
    @provide(key="database")
    async def factory() -> Database:
        return Database()

    assert factory.key == "database"


def test_provide_with_type_key_keyed_by_type() -> None:
    @provide(key=Database)
    async def factory() -> Database:
        return Database()

    assert factory.kind is ProviderKind.TYPE
    assert factory.key is Database


class _Meta(type):
    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        return super().__call__(*args, **kwargs)


class ServiceUnderMetaclass(metaclass=_Meta):
    def __init__(self, config: NamedDependency[str]) -> None:
        self.config = config


def test_class_with_call_signature_differing_from_init_raises() -> None:
    """``inspect.signature`` follows a metaclass ``__call__`` or a ``__new__``; the ``__init__``
    hints do not. When the two disagree, reading the class raises, naming the class."""
    with pytest.raises(DIRegistrationError, match="Cannot inspect the signature of ServiceUnderMetaclass") as exc_info:
        Provider(ServiceUnderMetaclass, kind="type", scope="app").resolve_signature()
    assert "'args' does not have a type annotation" in str(exc_info.value)


async def with_self(self: NamedDependency[str]) -> str:
    return self


async def with_cls(cls: NamedDependency[str]) -> str:
    return cls


@pytest.mark.parametrize(("factory", "name"), [(with_self, "self"), (with_cls, "cls")])
def test_function_parameter_named_self_or_cls_is_ordinary_parameter(factory: Any, name: str) -> None:
    provider = Provider(factory, kind="named", key="value")
    assert provider.dependencies == (InjectionParameter(parameter_name=name, key=name, kind=ProviderKind.NAMED),)


def test_init_first_parameter_not_named_self_is_receiver() -> None:
    """The first parameter of ``__init__`` is the receiver by position, not by name."""

    class Service:
        def __init__(this, config: NamedDependency[str]) -> None:  # pyright: ignore[reportSelfClsParameterName]
            this.config = config

    assert Provider(Service, kind="type", scope="app").dependencies == (
        InjectionParameter(parameter_name="config", key="config", kind=ProviderKind.NAMED),
    )


def test_seed_declares_without_factory() -> None:
    provider = Provider.seed("request")

    assert provider.fn is None
    assert provider.is_seed is True
    assert provider.key == "request"
    assert provider.kind is ProviderKind.NAMED
    assert provider.scope == "handler"  # DEFAULT_SCOPE
    assert provider.dependencies == ()
    assert provider.non_di_parameters == ()
    assert provider.sync_to_thread is False  # nothing to call, so nothing to offload
    assert repr(provider) == "Provider.seed('request', scope='handler')"


async def test_producing_seed_raises() -> None:
    provider = Provider.seed("request")
    with pytest.raises(DIResolutionError, match="is declared as a seed and has no callable"):
        await provider._produce({}, _CleanupStack())


def test_calling_seed_raises() -> None:
    with pytest.raises(DIResolutionError, match="is declared as a seed and has no callable"):
        Provider.seed("request")()


async def test_calling_decorated_factory_returns_value() -> None:

    @provide(scope="app")
    async def greeting() -> str:
        return "hi"

    assert await greeting() == "hi"


async def test_decorated_factory_takes_dependencies_as_arguments() -> None:
    """Dependencies are ordinary parameters when called directly."""

    @provide(scope="request")
    async def engine(dsn: NamedDependency[str]) -> str:
        return f"engine({dsn})"

    assert await engine(dsn="test") == "engine(test)"


def test_calling_sync_provider_runs_inline() -> None:
    """No thread hop, whatever ``sync_to_thread`` says."""

    @provide(scope="app", sync_to_thread=True)
    def number() -> int:
        return 41

    assert number() == 41


async def test_calling_generator_provider_returns_generator() -> None:

    @provide(scope="request")
    async def session() -> AsyncGenerator[str, None]:
        yield "session"

    generator = session()
    assert await anext(generator) == "session"
    await generator.aclose()


def test_wrapping_provider_in_provider_raises() -> None:

    @provide(scope="app")
    async def value() -> str:
        return "value"

    with pytest.raises(DIRegistrationError, match="already a Provider"):
        Provider(value, kind="named", key="other")


def test_dependency_marker_with_default_is_optional_dependency() -> None:
    async def fn(db: NamedDependency[str], cache: NamedDependency[str] = "none") -> str:
        return f"{db}/{cache}"

    provider = Provider(fn, kind="named", key="svc")
    by_name = {dependency.parameter_name: dependency for dependency in provider.dependencies}
    assert by_name["db"].optional is False
    assert by_name["cache"].optional is True


@pytest.mark.parametrize(
    ("annotation", "key", "kind"),
    [
        pytest.param(Annotated[Database, Dependency("db_session")], "db_session", ProviderKind.NAMED, id="name-key"),
        pytest.param(Annotated[Any, Dependency(Database)], Database, ProviderKind.TYPE, id="type-key"),
        pytest.param(
            Annotated[Database, Dependency("db.session")], "db.session", ProviderKind.NAMED, id="non-identifier-key"
        ),
    ],
)
def test_explicit_marker_decouples_key_from_parameter_name(annotation: Any, key: Any, kind: ProviderKind) -> None:
    async def factory(session: annotation) -> Config:  # pyright: ignore[reportInvalidTypeForm]
        return Config()

    provider = Provider(factory, kind="type")
    assert provider.dependencies == (InjectionParameter(parameter_name="session", key=key, kind=kind),)


def test_two_parameters_depend_on_one_named_key() -> None:
    async def factory(
        first: Annotated[Database, Dependency("db")],
        second: Annotated[Database, Dependency("db")],
    ) -> Config:
        return Config()

    provider = Provider(factory, kind="type")
    assert [(dep.parameter_name, dep.key) for dep in provider.dependencies] == [("first", "db"), ("second", "db")]


def test_marker_infer_kind_from_key() -> None:
    assert Dependency("db").kind is ProviderKind.NAMED
    assert Dependency(Database).kind is ProviderKind.TYPE


def test_marker_shorthand_type_aliases() -> None:
    assert get_args(NamedDependency[Database])[1] == Dependency(kind=ProviderKind.NAMED)
    assert get_args(TypeDependency[Database])[1] == Dependency(kind=ProviderKind.TYPE)
    assert Dependency(kind="named") == Dependency(kind=ProviderKind.NAMED)


def test_provider_without_key_or_kind_is_keyed_by_name() -> None:
    """A key decides the kind when there is one."""

    async def config() -> Config:
        return Config()

    assert Provider(config).kind is ProviderKind.NAMED
    assert Provider(config).key == "config"
    assert Provider(config, key=Config).kind is ProviderKind.TYPE
    assert Provider(None, key=Config).kind is ProviderKind.TYPE


def test_marker_without_key_and_kind_is_named() -> None:
    async def factory(db: Annotated[Database, Dependency()]) -> Config:
        return Config()

    assert Dependency() == Dependency(kind=ProviderKind.NAMED)
    assert Provider(factory, kind="type").dependencies == (
        InjectionParameter(parameter_name="db", key="db", kind=ProviderKind.NAMED),
    )


@pytest.mark.parametrize(
    ("key", "kind", "message"),
    [
        pytest.param(
            "db",
            "type",
            r"Dependency\(key='db', kind='type'\): String key does not match specified kind 'type'",
            id="string-key-with-type-kind",
        ),
        pytest.param(
            Database, "named", "Type key does not match specified kind 'named'", id="type-key-with-named-kind"
        ),
    ],
)
def test_marker_key_kind_contradiction_raises(key: Any, kind: Any, message: str) -> None:
    with pytest.raises(DIRegistrationError, match=message):
        Dependency(key, kind=kind)


def test_marker_unknown_kind_raises() -> None:
    with pytest.raises(
        DIRegistrationError,
        match=r"^Dependency\(key=None, kind='name'\): Unknown kind 'name', expected one of 'named', 'type'$",
    ):
        Dependency(kind="name")  # type: ignore[arg-type]


async def test_sync_provider_declared_non_blocking_runs_inline() -> None:
    def factory() -> int:
        return threading.get_ident()

    provider = Provider(factory, kind="named", sync_to_thread=False)

    assert await provider._produce({}, _CleanupStack()) == threading.get_ident()


def test_sync_function_without_sync_to_thread_raises() -> None:

    def factory() -> Database:
        return Database()

    with pytest.raises(DIRegistrationError, match="Missing 'sync_to_thread' on synchronous callable"):
        Provider(factory, kind="named")
    assert Provider(factory, kind="named", sync_to_thread=True).sync_to_thread is True
    assert Provider(factory, kind="named", sync_to_thread=False).sync_to_thread is False


def test_class_sync_to_thread_defaults_to_false() -> None:
    assert Provider(Database, kind="type").sync_to_thread is False
    assert Provider(Database, kind="type", sync_to_thread=True).sync_to_thread is True


@pytest.mark.parametrize("flag", [True, False])
def test_sync_to_thread_on_non_sync_callable_raises(flag: bool) -> None:
    async def factory() -> Database:
        return Database()

    async def generator() -> AsyncGenerator[Database, None]:
        yield Database()

    with pytest.raises(DIRegistrationError, match="not a synchronous callable"):
        Provider(factory, kind="named", sync_to_thread=flag)
    with pytest.raises(DIRegistrationError, match="not a synchronous callable"):
        Provider(generator, kind="named", sync_to_thread=flag)


async def test_sync_to_thread_false_keeps_caller_context() -> None:
    """A ContextVar the factory sets reaches the caller."""
    from contextvars import ContextVar

    var: ContextVar[str] = ContextVar("var", default="unset")

    def threaded() -> str:
        var.set("threaded")
        return "x"

    def inline() -> str:
        var.set("inline")
        return "x"

    await Provider(threaded, kind="named", key="a", sync_to_thread=True)._produce({}, _CleanupStack())
    assert var.get() == "unset"  # to_thread ran it in a copy of the context

    await Provider(inline, kind="named", key="b", sync_to_thread=False)._produce({}, _CleanupStack())
    assert var.get() == "inline"


def test_provider_carries_identity_of_wrapped_callable() -> None:

    @provide(scope="app")
    async def db_session(config: NamedDependency[str]) -> str:
        """Open a session."""
        return config

    assert db_session.__name__ == "db_session"  # type: ignore[attr-defined]
    assert db_session.__qualname__.endswith("db_session")  # type: ignore[attr-defined]
    assert db_session.__doc__ == "Open a session."
    assert db_session.__module__ == __name__
    assert db_session.__wrapped__ is db_session.fn  # type: ignore[attr-defined]
    assert list(inspect.signature(db_session).parameters) == ["config"]
    if hasattr(inspect, "markcoroutinefunction"):
        assert inspect.iscoroutinefunction(db_session)

    @provide(scope="app", sync_to_thread=False)
    def plain() -> int:
        return 1

    assert not inspect.iscoroutinefunction(plain)
    assert Provider.seed("request").__doc__ is Provider.__doc__  # a seed wraps nothing


def test_callable_attributes_do_not_replace_provider_fields() -> None:
    # an attribute of the class or instance named like a provider field does not replace the field
    class Service:
        scope = "request"

    assert Provider(Service, kind="type", scope="app").scope == "app"

    class Factory:
        def __init__(self) -> None:
            self.fn = "not the factory"

        async def __call__(self) -> int:
            return 1

    factory = Factory()
    assert Provider(factory, kind="named", key="value", scope="app").fn is factory


def test_provide_passes_sync_to_thread_through() -> None:
    @provide(sync_to_thread=False)
    def thing() -> int:
        return 1

    assert thing.sync_to_thread is False


def test_uninspectable_signature_raises() -> None:
    with pytest.raises(DIRegistrationError, match="Cannot inspect the signature"):
        Provider(min, kind="named", key="smallest", sync_to_thread=False).resolve_signature()


def test_unresolvable_return_annotation_raises() -> None:
    async def factory() -> "Missing":  # type: ignore[name-defined]  # noqa: F821
        raise NotImplementedError

    with pytest.raises(DIRegistrationError, match="Cannot inspect the signature.*Missing"):
        Provider(factory, kind="type").resolve_signature()


def test_callable_without_source_file_described_by_name_only(monkeypatch: pytest.MonkeyPatch) -> None:
    async def factory() -> str:
        return ""

    assert ".py" in _helpers._describe_callable(factory)  # normally the location is included

    # 'getsourcelines' still answers (from linecache, say) while 'getsourcefile' does not.
    # a location with no file to point at is no location at all
    monkeypatch.setattr(inspect, "getsourcefile", lambda fn: None)
    monkeypatch.setattr(inspect, "getsourcelines", lambda fn: ([], 1))
    assert ".py" not in _helpers._describe_callable(factory)


def test_marker_inside_optional_union_is_dependency() -> None:

    async def factory(db: NamedDependency[Database] | None = None) -> str:
        return "value"

    provider = Provider(factory, kind="named")

    assert provider.dependencies == (InjectionParameter("db", "db", ProviderKind.NAMED, optional=True),)
    assert provider.non_di_parameters == ()


async def none_outside(db: TypeDependency[Database] | None = None) -> str:
    return "value"


async def none_inside(db: TypeDependency[Database | None] = None) -> str:
    return "value"


@pytest.mark.parametrize("factory", [none_outside, none_inside])
def test_type_key_drops_none_from_either_optional_spelling(factory: Any) -> None:
    (dependency,) = Provider(factory, kind="named").dependencies
    assert dependency.key is Database
    assert dependency.optional is True


def test_marker_on_two_union_members_raises() -> None:
    async def factory(db: NamedDependency[Database] | NamedDependency[Config]) -> str:
        return "value"

    with pytest.raises(DIRegistrationError, match="more than one member of the union"):
        Provider(factory, kind="named").resolve_signature()


def test_marker_on_union_and_member_raises() -> None:

    async def factory(
        db: Annotated[Annotated[Database, Dependency("a")] | None, Dependency("b")] = None,
    ) -> Config:
        return Config()

    with pytest.raises(
        DIRegistrationError,
        match="contains a dependency marker on the union as well as a member of it. "
        "A parameter may only declare one dependency",
    ):
        Provider(factory, kind="type").resolve_signature()


async def test_partial_keyword_binding_is_not_a_dependency() -> None:
    """A keyword-bound parameter is neither a dependency nor optional; the binding is the caller's."""

    async def factory(db: NamedDependency[Database]) -> Database:
        return db

    bound = Database()
    provider = Provider(functools.partial(factory, db=bound), kind="named", key="factory")

    assert provider.dependencies == ()
    assert provider.non_di_parameters == ("db",)
    assert await provider._produce({}, _CleanupStack()) is bound


async def test_sync_wrapper_around_async_factory_is_sync_unless_marked() -> None:
    """The form is read off the callable, never off what it returns: a sync function returning an
    awaitable produces the awaitable; ``inspect.markcoroutinefunction`` makes it async."""

    async def factory() -> int:
        return 1

    def unmarked_wrapper() -> Any:
        return factory()

    value = await Provider(unmarked_wrapper, kind="named", key="value", sync_to_thread=False)._produce(
        {}, _CleanupStack()
    )
    assert asyncio.iscoroutine(value)
    value.close()

    if sys.version_info >= (3, 12):

        @inspect.markcoroutinefunction
        def marked_wrapper() -> Any:
            return factory()

        assert await Provider(marked_wrapper, kind="named", key="value")._produce({}, _CleanupStack()) == 1


@pytest.mark.parametrize(
    "provider",
    [
        pytest.param(Provider.seed(Database, scope="app"), id="shorthand"),
        pytest.param(Provider(None, kind="type", scope="app", key=Database), id="spelled out"),
    ],
)
def test_seed_is_provider_without_callable(provider: Provider) -> None:
    """``Provider.seed`` is shorthand for ``Provider(None, ...)`` with the kind read off the key."""
    assert provider.is_seed is True
    assert provider.fn is None
    assert provider.key is Database
    assert provider.kind is ProviderKind.TYPE
    assert provider.scope == "app"
    assert provider.dependencies == ()


def test_seed_without_key_raises() -> None:
    with pytest.raises(DIRegistrationError, match="Missing key for provider without factory"):
        Provider(None, kind="named")


def test_type_key_keeps_union_without_none() -> None:

    async def factory(engine: TypeDependency[Database | Config]) -> str:
        return "value"

    (dependency,) = Provider(factory, kind="named").dependencies

    assert dependency.key == Database | Config
    assert dependency.optional is False
