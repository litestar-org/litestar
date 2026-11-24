from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.utils import unique_name_for_scope

if TYPE_CHECKING:
    from collections.abc import Hashable

    from litestar.handlers.base import BaseRouteHandler

__all__ = ("TransferModelNaming", "TransferModelRegistry", "handler_name_scope")


class TransferModelRegistry:
    """The transfer model names allocated for one application, each stored under the key it was requested with."""

    __slots__ = ("_names", "_seen")

    def __init__(self) -> None:
        self._seen: set[str] = set()
        self._names: dict[Hashable, str] = {}

    def name_for(self, key: Hashable, preferred: str, qualified: str) -> str:
        """Return the name stored under ``key``, else allocate ``preferred``, then ``qualified``, then a numbered
        variant of ``qualified``, whichever is free first.
        """
        if (name := self._names.get(key)) is not None:
            return name
        if preferred not in self._seen:
            name = preferred
        elif qualified not in self._seen:
            name = qualified
        else:
            name = unique_name_for_scope(qualified, self._seen)
        self._seen.add(name)
        self._names[key] = name
        return name


class TransferModelNaming:
    """The view of a :class:`TransferModelRegistry` held by one backend, numbering repeated requests for one model."""

    __slots__ = ("_ordinals", "_registry", "_scope")

    def __init__(self, registry: TransferModelRegistry, scope: Hashable) -> None:
        self._registry = registry
        self._scope = scope
        self._ordinals: dict[str, int] = {}

    def name_for(self, *, is_data_field: bool, model_name: str, preferred: str, qualified: str) -> str:
        """Return the registry's name for the next request of ``model_name`` in this scope and direction."""
        ordinal = self._ordinals.get(model_name, 0)
        self._ordinals[model_name] = ordinal + 1
        return self._registry.name_for((self._scope, is_data_field, model_name, ordinal), preferred, qualified)


def handler_name_scope(handler: BaseRouteHandler) -> Hashable:
    """Return the value that identifies ``handler`` for naming, equal for every merge of the same registration."""
    return (
        str(handler),
        type(handler).__qualname__,
        tuple(sorted(handler.paths)),
        tuple(sorted(getattr(handler, "http_methods", ()))),
    )
