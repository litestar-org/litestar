import collections
import dataclasses
import functools
import inspect
from typing import TYPE_CHECKING, Any, Literal, Union, cast

from typing_extensions import Self

from litestar.exceptions import LitestarException
from litestar.middleware.base import ASGIMiddleware
from litestar.types import Middleware
from litestar.utils.module_loader import import_string

if TYPE_CHECKING:
    pass

__all__ = (
    "ConstraintViolationError",
    "CycleError",
    "MiddlewareConstraintError",
    "MiddlewareConstraints",
    "MiddlewareForwardRef",
    "check_middleware_constraints",
)


class MiddlewareConstraintError(LitestarException):
    pass


class ConstraintViolationError(MiddlewareConstraintError):
    pass


class CycleError(MiddlewareConstraintError):
    pass


@dataclasses.dataclass(frozen=True)
class MiddlewareForwardRef:
    """Forward reference to a middleware"""

    target: str
    """Absolute path to an importable name of the middleware"""
    ignore_import_error: bool
    r"""
    If 'True', ignore :exc:`ImportError`\ s will be ignored when resolving the
    middleware
    """

    @staticmethod
    @functools.cache
    def _resolve(target: str, ignore_not_found: bool) -> "Middleware | None":
        try:
            return cast("Middleware", import_string(target))
        except ImportError:
            if ignore_not_found:
                return None
            raise

    def resolve(self) -> "Middleware | None":
        """Resolve the reference to a concrete value by importing the target path.

        If ``ignore_import_error=True`` and an :exc:`ImportError` is raised, ignore the
        error and return ``None``
        """
        return self._resolve(self.target, self.ignore_import_error)


@dataclasses.dataclass
class _ResolvedMiddlewareConstraints:
    before: tuple["Middleware | MiddlewareFactory", ...]
    after: tuple["Middleware | MiddlewareFactory", ...]
    first: bool
    last: bool
    unique: bool

    @property
    def is_empty(self) -> bool:
        return not (self.before or self.after or self.first or self.last or self.unique)


@dataclasses.dataclass(frozen=True)
class MiddlewareConstraints:
    """Constraints for a middleware."""

    before: tuple["MiddlewareForwardRef | Middleware | MiddlewareFactory", ...] = ()
    """
    Tuple of middlewares that, if present, need to appear *before* the middleware this
    constraint is applied to
    """
    after: tuple["MiddlewareForwardRef | Middleware | MiddlewareFactory", ...] = ()
    """
    Tuple of middlewares that, if present, need to appear *after* the middleware this
    constraint is applied to
    """
    first: "bool | None" = None
    """
    If ``True``, require the middleware to be the first.
    Mutually exclusive with ``last=True``. Implicitly sets ``unique=True``
    """
    last: "bool | None" = None
    """
    If ``True``, require the middleware to be the last.
    Mutually exclusive with ``first=True``. Implicitly sets ``unique=True``
    """
    unique: "bool | None" = None
    """
    If ``True``, require the middleware to be the only one of its type
    """

    def __post_init__(self) -> None:
        if self.first:
            if self.last:
                raise MiddlewareConstraintError("Cannot set 'first=True' if 'last=True'")
            if self.unique is False:
                raise MiddlewareConstraintError("Cannot set 'first=True' if 'unique=False'")
            if self.after:
                raise MiddlewareConstraintError("Cannot set 'first=True' if if 'after' is not empty")

        if self.last:
            if self.unique is False:
                raise MiddlewareConstraintError("Cannot set 'last=True' if 'unique=False'")
            if self.before:
                raise MiddlewareConstraintError("Cannot set 'last=True' if 'before' is not empty")

    def require_unique(self, unique: bool) -> Self:
        """Return a new constraint with a ``unique`` value set"""
        return dataclasses.replace(self, unique=unique)

    def apply_first(self) -> Self:
        """Return a new constraint with ``first=True``. Overrides ``last=True``"""
        return dataclasses.replace(self, first=True, last=False, unique=True)

    def apply_last(self) -> Self:
        """Return a new constraint with ``first=True``. Overrides ``first=True``"""
        return dataclasses.replace(self, first=False, last=True, unique=True)

    def apply_before(
        self,
        other: "str | Middleware | MiddlewareFactory | MiddlewareForwardRef",
        ignore_import_error: bool = False,
    ) -> Self:
        """Return new :class:`~litestar.middleware.constraints.MiddlewareConstraints` with
        ``other`` added to existing ``before`` constraint.

        :param other: Middleware this middleware needs to be applied before. If passed a string,
            create a :class:`~litestar.middleware.constraints.MiddlewareForwardRef` that resolves
            to the actual middleware at runtime
        :param ignore_import_error: If ``True`` and ``other`` is a string, ignore the constraint if
            an :exc:`ImportError` occurs when trying to import it
        """
        if isinstance(other, str):
            other = MiddlewareForwardRef(target=other, ignore_import_error=ignore_import_error)

        return dataclasses.replace(self, before=(*self.before, other))

    def apply_after(
        self,
        other: "str | Middleware | MiddlewareFactory | MiddlewareForwardRef",
        ignore_import_error: bool = False,
    ) -> Self:
        """Return new :class:`~litestar.middleware.constraints.MiddlewareConstraints` with
        ``other`` added to existing ``after`` constraint.

        :param other: Middleware this middleware needs to be applied before. If passed a string,
            create a :class:`~litestar.middleware.constraints.MiddlewareForwardRef` that resolves
            to the actual middleware at runtime
        :param ignore_import_error: If ``True`` and ``other`` is a string, ignore the constraint if
            an :exc:`ImportError` occurs when trying to import it
        """
        if isinstance(other, str):
            other = MiddlewareForwardRef(target=other, ignore_import_error=ignore_import_error)

        return dataclasses.replace(self, after=(*self.after, other))

    @staticmethod
    def _resolve_middleware(
        middlewares: tuple["Middleware | MiddlewareFactory | MiddlewareForwardRef", ...],
    ) -> tuple["Middleware | MiddlewareFactory", ...]:
        resolved = []
        for middleware in middlewares:
            if isinstance(middleware, MiddlewareForwardRef):
                if (resolved_middleware := middleware.resolve()) is None:
                    continue
                middleware = resolved_middleware
            resolved.append(middleware)
        return tuple(resolved)

    def _resolve(self) -> _ResolvedMiddlewareConstraints:
        return _ResolvedMiddlewareConstraints(
            before=self._resolve_middleware(self.before),
            after=self._resolve_middleware(self.after),
            first=False if self.first is None else self.first,
            last=False if self.last is None else self.last,
            unique=False if self.unique is None else self.unique,
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


def _check_positional_constraints(
    graph: dict[object, list[object]],
    positions: dict[object, list[int]],
    directional_constraints: dict[tuple[object, object], Literal["before", "after"]],
) -> None:
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
                constraint = directional_constraints[(node_u, node_v)]
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
                    f"All instances of {first_name!r} must come {constraint} any "
                    f"instance of {second_name!r}. (Found instance of {first_name!r} "
                    f"at index {first_idx}, instance of {second_name!r} at index "
                    f"{second_idx})"
                )
                raise ConstraintViolationError(msg)


def _check_first_last_constraints(
    want_first: list[object],
    want_last: list[object],
    positions: dict[object, list[int]],
    total_count: int,
) -> None:
    if len(want_first) > 1:
        msg = f"Multiple middlewares define 'first=True': {', '.join(map(_fully_qualified_name, want_first))}"
        raise MiddlewareConstraintError(msg)

    if len(want_last) > 1:
        msg = f"Multiple middlewares define 'last=True': {', '.join(map(_fully_qualified_name, want_last))}"
        raise MiddlewareConstraintError(msg)

    if want_first:
        first = want_first[0]
        first_positions = positions[first]
        max_pos_first = max(first_positions)
        if max_pos_first > 0:
            msg = (
                f"Middleware {_fully_qualified_name(first)} must be at the top of "
                f"the stack. Found at index {', '.join(map(str, first_positions))}"
            )
            raise ConstraintViolationError(msg)

    if want_last:
        last = want_last[0]
        last_positions = positions[last]
        max_pos_first = min(last_positions)
        if max_pos_first != total_count - 1:
            msg = (
                f"Middleware {_fully_qualified_name(last)} must be at the end of "
                f"the stack. Found at index {', '.join(map(str, last_positions))}"
            )
            raise ConstraintViolationError(msg)


def _check_unique_constraints(unique: list[object], positions: dict[object, list[int]]) -> None:
    for middleware in unique:
        found_positions = positions[middleware]
        if len(found_positions) > 1:
            msg = (
                f"Middleware {_fully_qualified_name(middleware)!r} must be unique. "
                f"Found {len(found_positions)} instances (index "
                f"{', '.join(map(str, found_positions))})"
            )
            raise ConstraintViolationError(msg)


def check_middleware_constraints(middlewares: tuple[Middleware, ...]) -> None:
    want_first: list[object] = []
    want_last: list[object] = []
    unique: list[object] = []

    # simple "graph" that tracks a middleware and its neighbors, according to the spec
    # we're given. to keep things simple, we're converting all requirements into a form
    # of 'node -> list[predecessor]', and remember the original constraint
    graph: dict[object, list[object]] = collections.defaultdict(list)
    directional_constraints: dict[tuple[object, object], Literal["before", "after"]] = {}

    # keep track of the positions of *all* instances of a middleware; there may be more
    # than one instance of a specific type
    positions: collections.defaultdict[object, list[int]] = collections.defaultdict(list)

    for i, middleware in enumerate(middlewares):
        middleware_type: Union[object, type]
        if inspect.isfunction(middleware):
            positions[middleware].append(i)
            middleware_type = middleware
        else:
            # 'middleware' might be a class or an instance of a class
            middleware_type = type(middleware) if not inspect.isclass(middleware) else middleware
            for base in middleware_type.mro()[:-1]:  # pyright: ignore
                positions[base].append(i)

        if not (isinstance(middleware, ASGIMiddleware) and middleware.constraints):
            continue

        constraints = middleware.constraints._resolve()
        if constraints.is_empty:
            continue

        if constraints.first:
            want_first.append(middleware_type)
        if constraints.last:
            want_last.append(middleware_type)

        if constraints.unique:
            unique.append(middleware_type)

        for before in constraints.before:
            directional_constraints[(middleware_type, before)] = "before"
            graph[middleware_type].append(before)
        for after in constraints.after:
            directional_constraints[(after, middleware_type)] = "after"
            graph[after].append(middleware_type)

    _check_unique_constraints(
        unique=unique,
        positions=positions,
    )

    _check_first_last_constraints(
        want_first=want_first,
        want_last=want_last,
        positions=positions,
        total_count=len(middlewares),
    )

    _check_positional_constraints(
        graph=dict(graph),  # convert defaultdict to a regular dict to avoid accidental key creation
        positions=positions,
        directional_constraints=directional_constraints,
    )
