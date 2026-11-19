from __future__ import annotations

import sys
import typing
from dataclasses import dataclass, replace
from inspect import Signature, getmembers, isclass, ismethod
from itertools import chain
from typing import TYPE_CHECKING, Any, Self, get_type_hints

from litestar import connection, datastructures, params, types
from litestar.exceptions import ImproperlyConfiguredException
from litestar.types import Empty
from litestar.typing import FieldDefinition
from litestar.utils.typing import expand_type_var_in_type_hint
from litestar.utils.warnings import warn_signature_namespace_override

if TYPE_CHECKING:
    from collections.abc import Sequence

    from litestar.types import AnyCallable


__all__ = (
    "ParsedSignature",
    "add_types_to_signature_namespace",
    "get_fn_type_hints",
    "merge_signature_namespaces",
)

_GLOBAL_NAMES = {
    namespace: export
    for namespace, export in chain(
        tuple(getmembers(types)),
        tuple(getmembers(connection)),
        tuple(getmembers(datastructures)),
        tuple(getmembers(params)),
    )
    if namespace[0].isupper()
    and namespace in chain(types.__all__, connection.__all__, datastructures.__all__, params.__all__)
}
"""A mapping of names used for handler signature forward-ref resolution.

This allows users to include these names within an `if TYPE_CHECKING:` block in their handler module.
"""


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
        fn_to_inspect = fn_to_inspect.__func__  # pyright: ignore[reportFunctionMemberAccess]
    # Order important. If a litestar name has been overridden in the function module, we want
    # to use that instead of the litestar one.
    namespace = {
        **_GLOBAL_NAMES,
        **vars(typing),
        **vars(sys.modules[module_name]),
        **(namespace or {}),
    }
    hints = get_type_hints(fn_to_inspect, globalns=namespace, include_extras=True)

    return hints


@dataclass(frozen=True)
class ParsedSignature:
    """Parsed signature.

    This object is the primary source of handler/dependency signature information.

    The only post-processing that occurs is the conversion of any forward referenced type annotations.
    """

    __slots__ = ("original_signature", "parameters", "return_type")

    parameters: dict[str, FieldDefinition]
    """A mapping of parameter names to ParsedSignatureParameter instances."""
    return_type: FieldDefinition
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
        expanded_type_hints = expand_type_var_in_type_hint(fn_type_hints, signature_namespace)

        return cls.from_signature(signature, expanded_type_hints)

    @classmethod
    def from_property(cls, prop: property, signature_namespace: dict[str, Any]) -> Self:
        """Parse a 'property' signature. The signature will be that of 'property.fget'

        Args:
            prop: A :func:`property` instance.
            signature_namespace: mapping of names to types for forward reference resolution

        Returns:
            ParsedSignature
        """
        fn = prop.fget
        if fn is None:
            raise ImproperlyConfiguredException(f"Property {prop} has no getter function")
        signature = Signature()
        fn_type_hints = get_fn_type_hints(fn, namespace=signature_namespace)
        expanded_type_hints = expand_type_var_in_type_hint(fn_type_hints, signature_namespace)
        return cls.from_signature(signature, expanded_type_hints)

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
        )

        return_type = FieldDefinition.from_annotation(fn_type_hints.get("return", Any))

        return cls(
            parameters={p.name: p for p in parameters},
            return_type=return_type if "return" in fn_type_hints else replace(return_type, annotation=Empty),
            original_signature=signature,
        )


def add_types_to_signature_namespace(
    signature_types: Sequence[Any], signature_namespace: dict[str, Any]
) -> dict[str, Any]:
    """Add types to ith signature namespace mapping.

    Types are added mapped to their `__name__` attribute.

    Args:
        signature_types: A list of types to add to the signature namespace.
        signature_namespace: The signature namespace to add types to.

    Raises:
        AttributeError: If a type does not have a `__name__` attribute.

    Returns:
        The updated signature namespace.
    """
    return merge_signature_namespaces(
        signature_namespace=signature_namespace,
        additional_signature_namespace={signature_type.__name__: signature_type for signature_type in signature_types},
    )


def merge_signature_namespaces(
    signature_namespace: dict[str, Any], additional_signature_namespace: dict[str, Any]
) -> dict[str, Any]:
    """Add types to ith signature namespace mapping.

    Types are added mapped to their `__name__` attribute.

    Args:
        signature_namespace: The signature namespace to add types to.
        additional_signature_namespace: The signature namespace to merge

    Raises:
        AttributeError: If a type does not have a `__name__` attribute.

    Returns:
        The updated signature namespace.
    """
    for signature_key, signature_type in additional_signature_namespace.items():
        if signature_key in signature_namespace and signature_namespace.get(signature_key) != signature_type:
            warn_signature_namespace_override(signature_key)
    signature_namespace.update(additional_signature_namespace)
    return signature_namespace
