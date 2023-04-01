from __future__ import annotations

from dataclasses import dataclass
from inspect import Parameter, Signature
from typing import TYPE_CHECKING

from typing_extensions import get_args, get_origin

from starlite.types.empty import Empty
from starlite.utils.signature_parsing import get_fn_type_hints
from starlite.utils.typing import unwrap_annotation

if TYPE_CHECKING:
    from typing import Any

    from starlite.types import AnyCallable

__all__ = (
    "ParsedAnnotation",
    "ParsedParameter",
    "ParsedSignature",
)


@dataclass
class ParsedAnnotation:
    raw: Any
    """The annotation exactly as parsed from the callable."""
    annotation: Any
    """The annotation with any "wrapper" types removed, e.g. Annotated."""
    origin: type[Any] | None
    """The result of calling ``get_origin(annotation)`` after unwrapping Annotated, e.g. list."""
    args: tuple[Any, ...]
    """The result of calling ``get_args(annotation)`` after unwrapping Annotated, e.g. (int,)."""
    metadata: tuple[Any, ...]
    """Any metadata associated with the annotation via ``Annotated``."""

    @classmethod
    def from_parameter(cls, parameter: Parameter, fn_type_hints: dict[str, Any]) -> ParsedAnnotation:
        """Initialize ParsedSignatureAnnotation.

        Args:
            parameter: inspect.Parameter
            fn_type_hints: mapping of names to types for resolution of forward references.

        Returns:
            ParsedSignatureAnnotation.
        """

        raw = fn_type_hints.get(parameter.name, Empty)
        unwrapped, metadata = unwrap_annotation(raw)

        return ParsedAnnotation(
            raw=parameter.annotation,
            annotation=unwrapped,
            origin=get_origin(unwrapped),
            args=get_args(unwrapped),
            metadata=metadata,
        )


@dataclass
class ParsedParameter:
    """Represents the parameters of a callable for purpose of signature model generation."""

    name: str
    """The name of the parameter."""
    default: Any | Empty
    """The default value of the parameter."""
    annotation: ParsedAnnotation
    """The annotation of the parameter."""

    @classmethod
    def from_parameter(cls, parameter: Parameter, fn_type_hints: dict[str, Any]) -> ParsedParameter:
        """Initialize ParsedSignatureParameter.

        Args:
            parameter: inspect.Parameter
            fn_type_hints: mapping of names to types for resolution of forward references.

        Returns:
            ParsedSignatureParameter.
        """
        return ParsedParameter(
            name=parameter.name,
            default=Empty if parameter.default is Signature.empty else parameter.default,
            annotation=ParsedAnnotation.from_parameter(parameter, fn_type_hints),
        )


@dataclass
class ParsedSignature:
    """Parsed signature.

    This object is the primary source of handler/dependency signature information.

    The only post-processing that occurs is the conversion of any forward referenced type annotations.
    """

    parameters: dict[str, ParsedParameter]
    """A mapping of parameter names to ParsedSignatureParameter instances."""
    return_annotation: ParsedAnnotation
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
        raw_return_annotation = fn_type_hints.get("return", Empty)
        return_annotation, return_annotation_meta = unwrap_annotation(raw_return_annotation)
        return ParsedSignature(
            parameters={p.name: p for p in parameters},
            return_annotation=ParsedAnnotation(
                raw=raw_return_annotation,
                annotation=return_annotation,
                origin=get_origin(return_annotation),
                args=get_args(return_annotation),
                metadata=return_annotation_meta,
            ),
        )
