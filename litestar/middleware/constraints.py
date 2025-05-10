from __future__ import annotations

import collections
import dataclasses
import functools
import inspect
from typing import TYPE_CHECKING, Any, Literal, cast

from litestar.middleware.base import ASGIMiddleware
from litestar.utils.module_loader import import_string

if TYPE_CHECKING:
    from litestar.types import Middleware
    from litestar.types.composite_types import MiddlewareFactory

__all__ = (
    "MiddlewareConstraints",
    "check_middleware_constraints",
)


class CycleError(ValueError):
    pass


@dataclasses.dataclass(frozen=True)
class MiddlewareForwardRef:
    target: str
    ignore_not_found: bool

    @staticmethod
    @functools.cache
    def _resolve(target: str, ignore_not_found: bool) -> Middleware | None:
        try:
            return cast("Middleware", import_string(target))
        except ImportError:
            if ignore_not_found:
                return None
            raise

    def resolve(self) -> Middleware | None:
        return self._resolve(self.target, self.ignore_not_found)


@dataclasses.dataclass
class _ResolvedMiddlewareConstraints:
    before: tuple[Middleware | MiddlewareFactory, ...]
    after: tuple[Middleware | MiddlewareFactory, ...]

    @property
    def is_empty(self) -> bool:
        return not (self.before or self.after)


@dataclasses.dataclass(frozen=True)
class MiddlewareConstraints:
    before: tuple[MiddlewareForwardRef | Middleware | MiddlewareFactory, ...] = ()
    after: tuple[MiddlewareForwardRef | Middleware | MiddlewareFactory, ...] = ()

    def apply_before(
        self, other: str | Middleware | MiddlewareFactory | MiddlewareForwardRef, ignore_not_found: bool = False
    ) -> MiddlewareConstraints:
        if isinstance(other, str):
            other = MiddlewareForwardRef(target=other, ignore_not_found=ignore_not_found)

        return dataclasses.replace(self, before=(*self.before, other))

    def apply_after(
        self, other: str | Middleware | MiddlewareFactory | MiddlewareForwardRef, ignore_not_found: bool = False
    ) -> MiddlewareConstraints:
        if isinstance(other, str):
            other = MiddlewareForwardRef(target=other, ignore_not_found=ignore_not_found)

        return dataclasses.replace(self, after=(*self.after, other))

    @property
    def is_empty(self) -> bool:
        return not (self.before or self.after)

    @staticmethod
    def _resolve_middleware(
        middlewares: tuple[Middleware | MiddlewareFactory | MiddlewareForwardRef, ...],
    ) -> tuple[Middleware | MiddlewareFactory, ...]:
        resolved = []
        for middleware in middlewares:
            if isinstance(middleware, MiddlewareForwardRef):
                if (resolved_middleware := middleware.resolve()) is None:
                    continue
                middleware = resolved_middleware
            resolved.append(middleware)
        return tuple(resolved)

    def resolve(self) -> _ResolvedMiddlewareConstraints:
        return _ResolvedMiddlewareConstraints(
            before=self._resolve_middleware(self.before),
            after=self._resolve_middleware(self.after),
        )


def _fully_qualified_name(obj: Any) -> str:
    return f"{obj.__module__}.{obj.__qualname__}"


def _dfs(node: object, graph: dict[object, list[object]], visiting: set[object], visited: set[object]) -> bool:
    if node in visiting:
        return True

    if node in visited:
        return False

    visiting.add(node)
    if node in graph:
        for neighbor in graph[node]:
            if _dfs(neighbor, graph=graph, visiting=visiting, visited=visited):
                return True
    visiting.remove(node)
    visited.add(node)
    return False


def _detect_constraints_cycle(graph: dict[object, list[object]]) -> None:
    visited: set[object] = set()
    visiting: set[object] = set()

    for node in graph:
        if _dfs(node, graph=graph, visiting=visiting, visited=visited):
            raise CycleError()


def check_middleware_constraints(middlewares: tuple[Middleware, ...]) -> None:  # noqa: C901
    # simple "graph" that tracks a middleware and its neighbors, according to the spec
    # we're given. to keep things simple, we're converting all requirements into a form
    # of 'node -> list[predecessor]', and remember the original constraint
    graph: dict[object, list[object]] = collections.defaultdict(list)
    middleware_constraints: dict[tuple[object, object], Literal["before", "after"]] = {}

    # keep track of the positions of *all* instances of a middleware; there may be more
    # than one instance of a specific type
    positions: collections.defaultdict[object, list[int]] = collections.defaultdict(list)

    for i, middleware in enumerate(middlewares):
        middleware_type: object | type
        if inspect.isfunction(middleware):
            positions[middleware].append(i)
            middleware_type = middleware
        else:
            middleware_type = type(middleware) if not inspect.isclass(middleware) else middleware
            for base in middleware_type.mro()[:-1]:
                positions[base].append(i)

        if not (isinstance(middleware, ASGIMiddleware) and middleware.constraints):
            continue

        rp = middleware.constraints.resolve()
        if rp.is_empty:
            continue

        for before in rp.before:
            middleware_constraints[(middleware_type, before)] = "before"
            graph[middleware_type].append(before)
        for after in rp.after:
            middleware_constraints[(after, middleware_type)] = "after"
            graph[after].append(middleware_type)

    # done constructing; convert defaultdict to a regular dict to avoid accidental
    # key creation
    graph = dict(graph)
    _detect_constraints_cycle(graph)

    for node_u, predecessors in graph.items():
        u_positions = positions.get(node_u)
        if not u_positions:
            continue
        max_u_pos = max(u_positions)

        for node_v in predecessors:
            if not (v_positions := positions.get(node_v)):
                continue
            min_v_pos = min(v_positions)
            if max_u_pos >= min_v_pos:
                constraint = middleware_constraints[(node_u, node_v)]
                first = node_u
                second = node_v
                first_idx = max_u_pos
                second_idx = min_v_pos
                # since we've converted all constraints to a 'before' check while
                # building the graph, retrieve the original constraint type
                # ('before', 'after') for this violation, and flip the nodes of 'after'
                # constraints again, so we can construct an error message
                if constraint == "after":
                    first, second = second, first
                    first_idx, second_idx = second_idx, first_idx
                first_name = _fully_qualified_name(first)
                second_name = _fully_qualified_name(second)

                msg = (
                    f"Middleware constraint violated: All instances of {first_name!r} "
                    f"must come {constraint} any instance of {second_name!r}. (Found "
                    f"instance of {first_name!r} at index {first_idx}, instance of "
                    f"{second_name!r} at index {second_idx})"
                )
                raise ValueError(msg)
