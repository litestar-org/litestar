from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from inspect import Parameter, Signature
from typing import TYPE_CHECKING, Any, Union

from typing_extensions import Annotated, NotRequired, Required, get_args, get_origin

from starlite.datastructures.state import ImmutableState
from starlite.exceptions import ImproperlyConfiguredException
from starlite.types.builtin_types import UNION_TYPES, NoneType
from starlite.types.empty import Empty
from starlite.utils.signature_parsing import get_fn_type_hints
from starlite.utils.typing import get_safe_generic_origin, unwrap_annotation

if TYPE_CHECKING:
    from starlite.types import AnyCallable

__all__ = (
    "ParsedType",
    "ParsedParameter",
    "ParsedSignature",
)


@dataclass(frozen=True)
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

    @property
    def is_optional(self) -> bool:
        """Whether the annotation is Optional or not."""
        return bool(self.origin in UNION_TYPES and NoneType in self.args)

    @property
    def is_collection(self) -> bool:
        """Whether the annotation is a collection type or not."""
        return self.origin and issubclass(self.origin, Collection)

    def is_type_of(self, cls: type[Any]) -> bool:
        """Whether the annotation is a subclass of the given type.

        Args:
            cls: The type to check.

        Returns:
            Whether the annotation is a subclass of the given type.
        """
        if self.origin:
            if self.origin is Union:
                return False
            return issubclass(self.origin, cls)
        return self.annotation is not Any and issubclass(self.annotation, cls)

    @classmethod
    def from_annotation(cls, annotation: Any) -> ParsedType:
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
        return ParsedType(
            raw=annotation,
            annotation=unwrapped,
            origin=origin,
            args=args,
            metadata=metadata,
            is_annotated=Annotated in wrappers,
            is_required=Required in wrappers,
            is_not_required=NotRequired in wrappers,
            safe_generic_origin=get_safe_generic_origin(origin),
            inner_types=tuple(cls.from_annotation(arg) for arg in args),
        )


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
                "It must be typed to a subclass of `starlite.datastructures.ImmutableState` or "
                "`starlite.datastructures.State`."
            )

        return ParsedParameter(
            name=parameter.name,
            default=Empty if parameter.default is Signature.empty else parameter.default,
            parsed_type=ParsedType.from_annotation(annotation),
        )


@dataclass(frozen=True)
class ParsedSignature:
    """Parsed signature.

    This object is the primary source of handler/dependency signature information.

    The only post-processing that occurs is the conversion of any forward referenced type annotations.
    """

    __slots__ = (
        "parameters",
        "return_type",
    )

    parameters: dict[str, ParsedParameter]
    """A mapping of parameter names to ParsedSignatureParameter instances."""
    return_type: ParsedType
    """The return annotation of the callable."""

    @classmethod
    def from_fn(cls, fn: AnyCallable, signature_namespace: dict[str, Any]) -> ParsedSignature:
        """Parse a function signature into data used for the generation of a signature model.

        Args:
            fn: A callable.
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
        return ParsedSignature(
            parameters={p.name: p for p in parameters},
            return_type=ParsedType.from_annotation(fn_type_hints.get("return", Empty)),
        )
