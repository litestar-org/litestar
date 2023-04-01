from __future__ import annotations

import sys
import typing
from inspect import Signature, isclass, ismethod
from typing import Any, List

from typing_extensions import get_args, get_type_hints

from litestar._signature.parsing import ParsedSignatureParameter
from litestar.connection import Request, WebSocket
from litestar.datastructures import Headers, ImmutableState, State
from litestar.exceptions import ImproperlyConfiguredException
from litestar.params import DependencyKwarg, ParameterKwarg
from litestar.plugins import PluginMapping, SerializationPluginProtocol, get_plugin_for_value
from litestar.types import AnyCallable, Empty, Receive, Scope, Send, WebSocketScope

__all__ = ("get_fn_type_hints", "get_type_annotation_from_plugin", "parse_fn_signature")


_GLOBAL_NAMES = {
    "Headers": Headers,
    "ImmutableState": ImmutableState,
    "Receive": Receive,
    "Request": Request,
    "Scope": Scope,
    "Send": Send,
    "State": State,
    "WebSocket": WebSocket,
    "WebSocketScope": WebSocketScope,
}
"""A mapping of names used for handler signature forward-ref resolution.

This allows users to include these names within an `if TYPE_CHECKING:` block in their handler module.
"""


def get_fn_type_hints(fn: Any, namespace: dict[str, Any] | None = None) -> dict[str, Any]:
    """Resolve type hints for ``fn``.

    Args:
        fn: Thing that is having its signature modelled.
        namespace: Extra names for resolution of forward references.

    Returns:
        Mapping of names to types.
    """
    fn_to_inspect: Any = fn

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
        **vars(sys.modules[fn_to_inspect.__module__]),
        **(namespace or {}),
    }
    return get_type_hints(fn_to_inspect, globalns=namespace, include_extras=True)


def get_type_annotation_from_plugin(
    parameter: ParsedSignatureParameter,
    plugin: SerializationPluginProtocol,
    field_plugin_mappings: dict[str, PluginMapping],
) -> Any:
    """Use plugin declared for parameter annotation type to generate a pydantic model.

    Args:
        parameter:  ParsedSignatureParameter
        plugin: SerializationPluginProtocol
        field_plugin_mappings: A dictionary mapping fields for plugin mappings.

    Returns:
        A pydantic model to be used as a type
    """
    type_args = get_args(parameter.annotation)
    type_value = type_args[0] if type_args else parameter.annotation
    field_plugin_mappings[parameter.name] = PluginMapping(plugin=plugin, model_class=type_value)
    pydantic_model = plugin.to_data_container_class(model_class=type_value, parameter_name=parameter.name)
    return List[pydantic_model] if type_args else pydantic_model  # type:ignore[valid-type]


def parse_fn_signature(
    dependency_name_set: set[str],
    fn: AnyCallable,
    plugins: list[SerializationPluginProtocol],
    signature_namespace: dict[str, Any],
) -> tuple[list[ParsedSignatureParameter], Any, dict[str, PluginMapping], set[str]]:
    """Parse a function signature into data used for the generation of a signature model.

    Args:
        dependency_name_set: A set of dependency names
        fn: A callable.
        plugins: A list of plugins.
        signature_namespace: mapping of names to types for forward reference resolution

    Returns:
        A tuple containing the following values for generating a signature model: a mapping of field definitions, the
        callable's return annotation, a mapping of field names to plugins - if any, and an updated dependency name set.
    """
    signature = Signature.from_callable(fn)
    fn_name = getattr(fn, "__name__", "anonymous")

    field_plugin_mappings: dict[str, PluginMapping] = {}
    parsed_params: list[ParsedSignatureParameter] = []
    dependency_names: set[str] = set()
    fn_type_hints = get_fn_type_hints(fn, namespace=signature_namespace)

    parameters = (
        ParsedSignatureParameter.from_parameter(
            parameter=parameter, parameter_name=name, fn_name=fn_name, fn_type_hints=fn_type_hints
        )
        for name, parameter in signature.parameters.items()
        if name not in ("self", "cls")
    )
    for parameter in parameters:
        if parameter.name == "state" and not issubclass(parameter.annotation, ImmutableState):
            raise ImproperlyConfiguredException(
                f"The type annotation `{parameter.annotation}` is an invalid type for the 'state' reserved kwarg. "
                "It must be typed to a subclass of `litestar.datastructures.ImmutableState` or "
                "`litestar.datastructures.State`."
            )

        if isinstance(parameter.default, DependencyKwarg) and parameter.name not in dependency_name_set:
            if not parameter.optional and (
                isinstance(parameter.default, DependencyKwarg) and parameter.default.default is Empty
            ):
                raise ImproperlyConfiguredException(
                    f"Explicit dependency '{parameter.name}' for '{fn_name}' has no default value, "
                    f"or provided dependency."
                )
            dependency_names.add(parameter.name)

        if isinstance(parameter.default, ParameterKwarg) and parameter.default.value_type is not Empty:
            parameter.annotation = parameter.default.value_type

        if plugin := get_plugin_for_value(value=parameter.annotation, plugins=plugins):
            parameter.annotation = get_type_annotation_from_plugin(parameter, plugin, field_plugin_mappings)

        parsed_params.append(parameter)

    return parsed_params, fn_type_hints.get("return", Signature.empty), field_plugin_mappings, dependency_names
