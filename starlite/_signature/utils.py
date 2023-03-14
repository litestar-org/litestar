from __future__ import annotations

import sys
import typing
from inspect import isclass, ismethod
from typing import TYPE_CHECKING, Any, cast

from typing_extensions import get_type_hints

from starlite.connection import Request, WebSocket
from starlite.datastructures import Headers, ImmutableState, State
from starlite.exceptions import ImproperlyConfiguredException
from starlite.types import Receive, Scope, Send, WebSocketScope

__all__ = ("get_fn_type_hints", "get_signature_model")


if TYPE_CHECKING:
    from starlite._signature.models import SignatureModel


STARLITE_GLOBAL_NAMES = {
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


def get_signature_model(value: Any) -> type[SignatureModel]:
    """Retrieve and validate the signature model from a provider or handler."""
    try:
        return cast("type[SignatureModel]", value.signature_model)
    except AttributeError as e:  # pragma: no cover
        raise ImproperlyConfiguredException(f"The 'signature_model' attribute for {value} is not set") from e


def get_fn_type_hints(fn: Any) -> dict[str, Any]:
    """Resolve type hints for ``fn``.

    Args:
        fn: Thing that is having its signature modelled.

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

    try:
        module = sys.modules[fn_to_inspect.__module__]
    except AttributeError:
        module_namespace = {}
    else:
        module_namespace = vars(module)

    # Order important. If a starlite name has been overridden in the function module, we want
    # to use that instead of the starlite one.
    types = vars(typing)
    namespace = {**STARLITE_GLOBAL_NAMES, **module_namespace, **types}
    return get_type_hints(fn_to_inspect, globalns=namespace)
