from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from inspect import Parameter, Signature
from typing import TYPE_CHECKING

from typing_extensions import Annotated, NotRequired, Required, get_args, get_origin

from starlite.types.empty import Empty
from starlite.types.builtin_types import UNION_TYPES, NoneType
from starlite.utils.signature_parsing import get_fn_type_hints
from starlite.utils.typing import get_safe_generic_origin, unwrap_annotation

if TYPE_CHECKING:
    from typing import Any

    from starlite.types import AnyCallable

__all__ = (
    "ParsedType",
    "ParsedParameter",
    "ParsedSignature",
)


@dataclass
class ParsedType:
    """Represents a type annotation."""

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
    inner_annotations: tuple[ParsedType, ...]
    """The type's generic args parsed as ``ParsedType``, if applicable."""

    @property
    def is_optional(self) -> bool:
        """Whether the annotation is Optional or not."""
        return bool(self.origin in UNION_TYPES and NoneType in self.args)

    @property
    def is_collection(self) -> bool:
        """Whether the annotation is a collection type or not."""
        return self.origin and issubclass(self.origin, Collection)

    @classmethod
    def from_annotation(cls, annotation: Parameter) -> ParsedType:
        """Initialize ParsedSignatureAnnotation.

        Args:
            annotation: The type annotation. This should be extracted from the return of
                ``get_type_hints(..., include_extras=True)`` so that forward references are resolved and recursive
                ``Annotated`` types are flattened.

        Returns:
            ParsedSignatureAnnotation.
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
            inner_annotations=tuple(cls.from_annotation(arg) for arg in args),
        )


@dataclass
class ParsedParameter:
    """Represents the parameters of a callable."""

    name: str
    """The name of the parameter."""
    default: Any | Empty
    """The default value of the parameter."""
    annotation: ParsedType
    """The annotation of the parameter."""

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
        return ParsedParameter(
            name=parameter.name,
            default=Empty if parameter.default is Signature.empty else parameter.default,
            annotation=ParsedType.from_annotation(fn_type_hints[parameter.name]),
        )


@dataclass
class ParsedSignature:
    """Parsed signature.

    This object is the primary source of handler/dependency signature information.

    The only post-processing that occurs is the conversion of any forward referenced type annotations.
    """

    parameters: dict[str, ParsedParameter]
    """A mapping of parameter names to ParsedSignatureParameter instances."""
    return_annotation: ParsedType
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
            return_annotation=ParsedType.from_annotation(fn_type_hints.get("return", Empty)),
        )
