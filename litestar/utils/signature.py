from __future__ import annotations

import sys
import typing
from collections.abc import Collection, Mapping
from dataclasses import dataclass
from inspect import Parameter, Signature, getmembers, isclass, ismethod
from itertools import chain
from typing import Any, AnyStr, ForwardRef, TypeVar, Union

from typing_extensions import Annotated, NotRequired, Required, Self, get_args, get_origin, get_type_hints

from litestar import connection, datastructures, types
from litestar.datastructures import ImmutableState
from litestar.enums import RequestEncodingType
from litestar.exceptions import ImproperlyConfiguredException
from litestar.params import BodyKwarg, DependencyKwarg, ParameterKwarg
from litestar.types import AnyCallable, Empty
from litestar.types.builtin_types import UNION_TYPES, NoneType
from litestar.utils.typing import get_safe_generic_origin, unwrap_annotation

_GLOBAL_NAMES = {
    namespace: export
    for namespace, export in chain(
        tuple(getmembers(types)), tuple(getmembers(connection)), tuple(getmembers(datastructures))
    )
    if namespace[0].isupper()
    and namespace in chain(types.__all__, connection.__all__, datastructures.__all__)  # pyright: ignore
}
"""A mapping of names used for handler signature forward-ref resolution.

This allows users to include these names within an `if TYPE_CHECKING:` block in their handler module.
"""

__all__ = (
    "get_fn_type_hints",
    "ParsedType",
    "ParsedParameter",
    "ParsedSignature",
    "infer_request_encoding_from_parameter",
)


def get_fn_type_hints(fn: Any, namespace: dict[str, Any] | None = None) -> dict[str, Any]:
    """Resolve type hints for ``fn``.

    Args:
        fn: Callable that is being inspected
        namespace: Extra names for resolution of forward references.

    Returns:
        Mapping of names to types.
    """
    fn_to_inspect: Any = fn

    module_name = fn_to_inspect.__module__

    if isclass(fn_to_inspect):
        fn_to_inspect = fn_to_inspect.__init__

    # detect objects that are not functions and that have a `__call__` method
    if callable(fn_to_inspect) and ismethod(fn_to_inspect.__call__):
        fn_to_inspect = fn_to_inspect.__call__

    # inspect the underlying function for methods
    if hasattr(fn_to_inspect, "__func__"):
        fn_to_inspect = fn_to_inspect.__func__

    # Order important. If a litestar name has been overridden in the function module, we want
    # to use that instead of the litestar one.
    namespace = {
        **_GLOBAL_NAMES,
        **vars(typing),
        **vars(sys.modules[module_name]),
        **(namespace or {}),
    }
    return get_type_hints(fn_to_inspect, globalns=namespace, include_extras=True)


@dataclass(frozen=True, init=False)
class ParsedType:
    """Represents a type annotation."""

    __slots__ = (
        "raw",
        "annotation",
        "origin",
        "args",
        "metadata",
        "is_annotated",
        "is_required",
        "is_not_required",
        "safe_generic_origin",
        "inner_types",
    )

    raw: Any
    """The annotation exactly as received."""
    annotation: Any
    """The annotation with any "wrapper" types removed, e.g. Annotated."""
    origin: Any
    """The result of calling ``get_origin(annotation)`` after unwrapping Annotated, e.g. list."""
    args: tuple[Any, ...]
    """The result of calling ``get_args(annotation)`` after unwrapping Annotated, e.g. (int,)."""
    metadata: tuple[Any, ...]
    """Any metadata associated with the annotation via ``Annotated``."""
    is_annotated: bool
    """Whether the annotation included ``Annotated`` or not."""
    is_required: bool
    """Whether the annotation included ``Required`` or not."""
    is_not_required: bool
    """Whether the annotation included ``NotRequired`` or not."""
    safe_generic_origin: Any
    """An equivalent type to ``origin`` that can be safely used as a generic type across all supported Python versions.

    This is to serve safely rebuilding a generic outer type with different args at runtime.
    """
    inner_types: tuple[ParsedType, ...]
    """The type's generic args parsed as ``ParsedType``, if applicable."""

    def __init__(self, annotation: Any) -> None:
        """Initialize ParsedType.

        Args:
            annotation: The type annotation. This should be extracted from the return of
                ``get_type_hints(..., include_extras=True)`` so that forward references are resolved and recursive
                ``Annotated`` types are flattened.

        Returns:
            ParsedType
        """
        unwrapped, metadata, wrappers = unwrap_annotation(annotation)
        origin = get_origin(unwrapped)
        args = get_args(unwrapped)
        object.__setattr__(self, "raw", annotation)
        object.__setattr__(self, "annotation", unwrapped)
        object.__setattr__(self, "origin", origin)
        object.__setattr__(self, "args", args)
        object.__setattr__(self, "metadata", metadata)
        object.__setattr__(self, "is_annotated", Annotated in wrappers)
        object.__setattr__(self, "is_required", Required in wrappers)
        object.__setattr__(self, "is_not_required", NotRequired in wrappers)
        object.__setattr__(self, "safe_generic_origin", get_safe_generic_origin(origin))
        object.__setattr__(self, "inner_types", tuple(ParsedType(arg) for arg in args))

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, ParsedType):
            return False

        if self.origin:
            return bool(self.origin == other.origin and self.inner_types == other.inner_types)

        return bool(self.annotation == other.annotation)

    @property
    def is_forward_ref(self) -> bool:
        """Whether the annotation is a forward reference or not."""
        return isinstance(self.annotation, (str, ForwardRef))

    @property
    def is_mapping(self) -> bool:
        """Whether the annotation is a mapping or not."""
        return self.is_subclass_of(Mapping)

    @property
    def is_tuple(self) -> bool:
        """Whether the annotation is a ``tuple`` or not."""
        return self.is_subclass_of(tuple)

    @property
    def is_type_var(self) -> bool:
        """Whether the annotation is a TypeVar or not."""
        return isinstance(self.annotation, TypeVar)

    @property
    def is_union(self) -> bool:
        """Whether the annotation is a union type or not."""
        return self.origin in UNION_TYPES

    @property
    def is_optional(self) -> bool:
        """Whether the annotation is Optional or not."""
        return bool(self.is_union and NoneType in self.args)

    @property
    def is_collection(self) -> bool:
        """Whether the annotation is a collection type or not."""
        return bool(self.origin and self.origin is not Union and issubclass(self.origin, Collection))

    def is_subclass_of(self, cl: type[Any] | tuple[type[Any], ...]) -> bool:
        """Whether the annotation is a subclass of the given type.

        Where ``self.annotation`` is a union type, this method will always return ``False``. While this is not
        strictly correct, we intend on revisiting this once a concrete use-case is to hand.

        Args:
            cl: The type to check, or tuple of types. Passed as 2nd argument to ``issubclass()``.

        Returns:
            Whether the annotation is a subtype of the given type(s).
        """
        if self.origin:
            return self.origin not in UNION_TYPES and issubclass(self.origin, cl)
        if self.annotation is AnyStr:
            return issubclass(str, cl) or issubclass(bytes, cl)
        return self.annotation is not Any and not self.is_type_var and issubclass(self.annotation, cl)

    def has_inner_subclass_of(self, cl: type[Any] | tuple[type[Any], ...]) -> bool:
        """Whether any generic args are a subclass of the given type.

        Args:
            cl: The type to check, or tuple of types. Passed as 2nd argument to ``issubclass()``.

        Returns:
            Whether any of the type's generic args are a subclass of the given type.
        """
        return any(t.is_subclass_of(cl) for t in self.inner_types)


@dataclass(frozen=True)
class ParsedParameter:
    """Represents the parameters of a callable."""

    __slots__ = (
        "name",
        "default",
        "parsed_type",
    )

    name: str
    """The name of the parameter."""
    default: Any | Empty
    """The default value of the parameter."""
    parsed_type: ParsedType
    """The annotation of the parameter."""

    @property
    def kwarg_container(self) -> ParameterKwarg | BodyKwarg | DependencyKwarg | None:
        """A kwarg container, if any"""
        for value in (*self.metadata, self.default):
            if isinstance(value, (ParameterKwarg, BodyKwarg, DependencyKwarg)):
                return value
        return None

    @property
    def metadata(self) -> tuple[Any, ...]:
        """The metadata of the parameter's annotation."""
        return self.parsed_type.metadata

    @property
    def annotation(self) -> Any:
        """The annotation of the parameter."""
        return self.parsed_type.annotation

    @property
    def has_default(self) -> bool:
        """Whether the parameter has a default value or not."""
        return self.default is not Empty

    @classmethod
    def from_parameter(cls, parameter: Parameter, fn_type_hints: dict[str, Any]) -> ParsedParameter:
        """Initialize ParsedSignatureParameter.

        Args:
            parameter: inspect.Parameter
            fn_type_hints: mapping of names to types. Should be result of ``get_type_hints()``, preferably via the
            :attr:``get_fn_type_hints() <.utils.signature_parsing.get_fn_type_hints>` helper.

        Returns:
            ParsedSignatureParameter.
        """
        try:
            annotation = fn_type_hints[parameter.name]
        except KeyError as err:
            raise ImproperlyConfiguredException(
                f"'{parameter.name}' does not have a type annotation. If it should receive any value, use 'Any'."
            ) from err

        if parameter.name == "state" and not issubclass(annotation, ImmutableState):
            raise ImproperlyConfiguredException(
                f"The type annotation `{annotation}` is an invalid type for the 'state' reserved kwarg. "
                "It must be typed to a subclass of `litestar.datastructures.ImmutableState` or "
                "`litestar.datastructures.State`."
            )

        return ParsedParameter(
            name=parameter.name,
            default=Empty if parameter.default is Signature.empty else parameter.default,
            parsed_type=ParsedType(annotation),
        )


@dataclass(frozen=True)
class ParsedSignature:
    """Parsed signature.

    This object is the primary source of handler/dependency signature information.

    The only post-processing that occurs is the conversion of any forward referenced type annotations.
    """

    __slots__ = ("parameters", "return_type", "original_signature")

    parameters: dict[str, ParsedParameter]
    """A mapping of parameter names to ParsedSignatureParameter instances."""
    return_type: ParsedType
    """The return annotation of the callable."""
    original_signature: Signature
    """The raw signature as returned by :func:`inspect.signature`"""

    @classmethod
    def from_fn(cls, fn: AnyCallable, signature_namespace: dict[str, Any]) -> Self:
        """Parse a function signature.

        Args:
            fn: Any callable.
            signature_namespace: mapping of names to types for forward reference resolution

        Returns:
            ParsedSignature
        """
        signature = Signature.from_callable(fn)
        fn_type_hints = get_fn_type_hints(fn, namespace=signature_namespace)

        parameters = (
            ParsedParameter.from_parameter(parameter=parameter, fn_type_hints=fn_type_hints)
            for name, parameter in signature.parameters.items()
            if name not in ("self", "cls")
        )
        return cls(
            parameters={p.name: p for p in parameters},
            return_type=ParsedType(fn_type_hints.get("return", Empty)),
            original_signature=signature,
        )

    @classmethod
    def from_signature(cls, signature: Signature, signature_namespace: dict[str, Any]) -> Self:
        """Parse an :class:`inspect.Signature` instance.

        Python's `get_type_hints()` function does not support parsing signatures directly, so we need to create a dummy
        function to pass to it. Maybe there's a better way to do this, but this does work.

        Args:
            signature: An :class:`inspect.Signature` instance.
            signature_namespace: mapping of names to types for forward reference resolution

        Returns:
            ParsedSignature
        """

        def fn() -> None:
            ...

        fn.__signature__ = signature  # type:ignore[attr-defined]
        fn.__annotations__ = {p.name: p.annotation for p in signature.parameters.values()}
        return cls.from_fn(fn, signature_namespace)


def infer_request_encoding_from_parameter(param: ParsedParameter) -> RequestEncodingType | str:
    """Infer the request encoding type from a parsed type.

    Args:
        param: The parsed parameter to infer the request encoding type from.

    Returns:
        The inferred request encoding type.
    """
    if param.has_default and isinstance(param.default, BodyKwarg):
        return param.default.media_type
    if param.parsed_type.metadata:
        for item in param.parsed_type.metadata:
            if isinstance(item, BodyKwarg):
                return item.media_type
    return RequestEncodingType.JSON
