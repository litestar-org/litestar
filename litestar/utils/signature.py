from __future__ import annotations

import sys
import typing
from dataclasses import dataclass
from inspect import Parameter, Signature, getmembers, isclass, ismethod
from itertools import chain
from typing import Any

from typing_extensions import Self, get_type_hints

from litestar import connection, datastructures, types
from litestar.datastructures import ImmutableState
from litestar.enums import RequestEncodingType
from litestar.exceptions import ImproperlyConfiguredException
from litestar.params import BodyKwarg, DependencyKwarg, ParameterKwarg
from litestar.types import AnyCallable, Empty
from litestar.typing import ParsedType
from litestar.utils.dataclass import simple_asdict

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

    def copy_with(self, **kwargs: Any) -> Self:
        """Create a copy of the parameter with the given attributes updated.

        Args:
            kwargs: Attributes to update.

        Returns:
            ParsedParameter
        """
        data = {**simple_asdict(self, convert_nested=False), **kwargs}
        return type(self)(**data)


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
