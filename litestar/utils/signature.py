from __future__ import annotations

import sys
import typing
from copy import deepcopy
from dataclasses import dataclass, replace
from inspect import Signature, getmembers, isclass, ismethod
from itertools import chain
from typing import Any

from typing_extensions import Self, get_type_hints

from litestar import connection, datastructures, types
from litestar.enums import RequestEncodingType
from litestar.params import BodyKwarg
from litestar.types import Empty
from litestar.typing import FieldDefinition

if typing.TYPE_CHECKING:
    from litestar.types import AnyCallable

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
    "ParsedSignature",
    "infer_request_encoding_from_field_definition",
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


@dataclass(frozen=True)
class ParsedSignature:
    """Parsed signature.

    This object is the primary source of handler/dependency signature information.

    The only post-processing that occurs is the conversion of any forward referenced type annotations.
    """

    __slots__ = ("parameters", "return_type", "original_signature")

    parameters: dict[str, FieldDefinition]
    """A mapping of parameter names to ParsedSignatureParameter instances."""
    return_type: FieldDefinition
    """The return annotation of the callable."""
    original_signature: Signature
    """The raw signature as returned by :func:`inspect.signature`"""

    def __deepcopy__(self, memo: dict[str, Any]) -> Self:
        return type(self)(
            parameters={k: deepcopy(v) for k, v in self.parameters.items()},
            return_type=deepcopy(self.return_type),
            original_signature=deepcopy(self.original_signature),
        )

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

        return cls.from_signature(signature, fn_type_hints)

    @classmethod
    def from_signature(cls, signature: Signature, fn_type_hints: dict[str, type]) -> Self:
        """Parse an :class:`inspect.Signature` instance.

        Args:
            signature: An :class:`inspect.Signature` instance.
            fn_type_hints: mapping of types

        Returns:
            ParsedSignature
        """

        parameters = tuple(
            FieldDefinition.from_parameter(parameter=parameter, fn_type_hints=fn_type_hints)
            for name, parameter in signature.parameters.items()
            if name not in ("self", "cls")
        )

        return_type = FieldDefinition.from_annotation(fn_type_hints.get("return", Any))

        return cls(
            parameters={p.name: p for p in parameters},
            return_type=return_type if "return" in fn_type_hints else replace(return_type, annotation=Empty),
            original_signature=signature,
        )


def infer_request_encoding_from_field_definition(field_definition: FieldDefinition) -> RequestEncodingType | str:
    """Infer the request encoding type from a parsed type.

    Args:
        field_definition: The parsed parameter to infer the request encoding type from.

    Returns:
        The inferred request encoding type.
    """
    if field_definition.kwarg_definition and isinstance(field_definition.kwarg_definition, BodyKwarg):
        return field_definition.kwarg_definition.media_type
    if isinstance(field_definition.default, BodyKwarg):
        return field_definition.default.media_type
    return RequestEncodingType.JSON
