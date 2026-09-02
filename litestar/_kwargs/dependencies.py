from __future__ import annotations

from typing import TYPE_CHECKING, Any

from litestar.exceptions import ImproperlyConfiguredException

__all__ = (
    "DependencyContainer",
    "DependencyGraph",
    "create_dependency_batches",
    "create_dependency_graph",
    "map_dependencies_recursively",
    "resolve_dependency",
)


if TYPE_CHECKING:
    from collections.abc import Iterable

    from litestar._kwargs.cleanup import DependencyCleanupGroup
    from litestar.connection import ASGIConnection
    from litestar.di import Provide


class DependencyContainer:
    """Dependency graph of a given combination of ``Route`` + ``RouteHandler``"""

    __slots__ = ("dependencies", "key", "provide")

    def __init__(self, key: str, provide: Provide, dependencies: list[DependencyContainer]) -> None:
        """Initialize a dependency.

        Args:
            key: The dependency key
            provide: Provider
            dependencies: List of child nodes
        """
        self.key = key
        self.provide = provide
        self.dependencies = dependencies

    def __eq__(self, other: Any) -> bool:
        # check if memory address is identical, otherwise compare attributes
        return other is self or (isinstance(other, self.__class__) and other.key == self.key)

    def __hash__(self) -> int:
        return hash(self.key)


class DependencyGraph:
    """Canonical graph of the dependencies reachable by a handler."""

    __slots__ = ("nodes", "paths", "roots")

    def __init__(self) -> None:
        self.nodes: dict[str, DependencyContainer] = {}
        self.paths: dict[str, tuple[str, ...]] = {}
        self.roots: set[DependencyContainer] = set()


def create_dependency_graph(dependency_keys: Iterable[str], dependencies: dict[str, Provide]) -> DependencyGraph:
    """Create a canonical graph containing only dependencies reachable from ``dependency_keys``.

    Each dependency key is represented by exactly one :class:`DependencyContainer`. The graph is traversed
    iteratively so deeply nested dependency chains don't consume the Python call stack. Cycles are rejected with the
    dependency path that introduced them.

    Args:
        dependency_keys: Keys directly requested by the handler.
        dependencies: All providers available to the handler.

    Returns:
        The reachable dependency graph.

    Raises:
        ImproperlyConfiguredException: If the dependency graph contains a cycle.
    """
    graph = DependencyGraph()
    adjacency: dict[str, tuple[str, ...]] = {}
    states: dict[str, int] = {}

    def get_node(key: str) -> DependencyContainer:
        if (node := graph.nodes.get(key)) is None:
            node = graph.nodes[key] = DependencyContainer(key=key, provide=dependencies[key], dependencies=[])
        return node

    def get_sub_dependency_keys(key: str) -> tuple[str, ...]:
        if (keys := adjacency.get(key)) is None:
            keys = adjacency[key] = tuple(
                field_name for field_name in dependencies[key].signature_model._fields if field_name in dependencies
            )
        return keys

    for root_key in dependency_keys:
        root = get_node(root_key)
        graph.roots.add(root)
        graph.paths.setdefault(root_key, (root_key,))

        if states.get(root_key) == 2:
            continue

        states[root_key] = 1
        stack: list[tuple[str, int]] = [(root_key, 0)]

        while stack:
            key, next_child_index = stack[-1]
            sub_dependency_keys = get_sub_dependency_keys(key)

            if next_child_index == len(sub_dependency_keys):
                states[key] = 2
                stack.pop()
                continue

            sub_dependency_key = sub_dependency_keys[next_child_index]
            stack[-1] = (key, next_child_index + 1)
            graph.nodes[key].dependencies.append(get_node(sub_dependency_key))

            state = states.get(sub_dependency_key, 0)
            if state == 1:
                active_path = [active_key for active_key, _ in stack]
                cycle_start = active_path.index(sub_dependency_key)
                cycle = [*active_path[cycle_start:], sub_dependency_key]
                raise ImproperlyConfiguredException(f"Dependency cycle detected: {' -> '.join(cycle)}")

            if state == 0:
                graph.paths[sub_dependency_key] = (*graph.paths[key], sub_dependency_key)
                states[sub_dependency_key] = 1
                stack.append((sub_dependency_key, 0))

    return graph


async def resolve_dependency(
    dependency: DependencyContainer,
    connection: ASGIConnection,
    kwargs: dict[str, Any],
    cleanup_group: DependencyCleanupGroup,
) -> None:
    """Resolve a given instance of :class:`Dependency <litestar._kwargs.Dependency>`.

    All required sub dependencies must already
    be resolved into the kwargs. The result of the dependency will be stored in the kwargs.

    Args:
        dependency: An instance of :class:`Dependency <litestar._kwargs.Dependency>`
        connection: An instance of :class:`Request <litestar.connection.Request>` or
            :class:`WebSocket <litestar.connection.WebSocket>`.
        kwargs: Any kwargs to pass to the dependency, the result will be stored here as well.
        cleanup_group: DependencyCleanupGroup to which generators returned by ``dependency`` will be added
    """
    signature_model = dependency.provide.signature_model
    dependency_kwargs = (
        signature_model.parse_values_from_connection_kwargs(connection=connection, kwargs=kwargs)
        if signature_model._fields
        else {}
    )
    value = await dependency.provide(**dependency_kwargs)

    if dependency.provide.has_sync_generator_dependency:
        cleanup_group.add(value)
        value = next(value)
    elif dependency.provide.has_async_generator_dependency:
        cleanup_group.add(value)
        value = await anext(value)

    kwargs[dependency.key] = value


def create_dependency_batches(expected_dependencies: set[DependencyContainer]) -> list[set[DependencyContainer]]:
    """Calculate batches for all dependencies, recursively.

    Args:
        expected_dependencies: A set of all direct :class:`Dependencies <litestar._kwargs.Dependency>`.

    Returns:
        A list of batches.
    """
    dependencies_to: dict[DependencyContainer, set[DependencyContainer]] = {}
    for dependency in expected_dependencies:
        if dependency not in dependencies_to:
            map_dependencies_recursively(dependency, dependencies_to)

    batches = []
    while dependencies_to:
        current_batch = {
            dependency
            for dependency, remaining_sub_dependencies in dependencies_to.items()
            if not remaining_sub_dependencies
        }

        for dependency in current_batch:
            del dependencies_to[dependency]
            for others_dependencies in dependencies_to.values():
                others_dependencies.discard(dependency)

        batches.append(current_batch)

    return batches


def map_dependencies_recursively(
    dependency: DependencyContainer, dependencies_to: dict[DependencyContainer, set[DependencyContainer]]
) -> None:
    """Recursively map dependencies to their sub dependencies.

    Args:
        dependency: The current dependency to map.
        dependencies_to: A map of dependency to its sub dependencies.
    """
    dependencies_to[dependency] = set(dependency.dependencies)
    for sub in dependency.dependencies:
        if sub not in dependencies_to:
            map_dependencies_recursively(sub, dependencies_to)
