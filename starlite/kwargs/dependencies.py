from inspect import isasyncgen, isgenerator
from typing import TYPE_CHECKING, Any, Dict, List, Set

from starlite.signature import get_signature_model
from starlite.utils.compat import async_next

if TYPE_CHECKING:
    from starlite.connection import ASGIConnection
    from starlite.datastructures.provide import DependencyCleanupGroup, Provide


class Dependency:
    """Dependency graph of a given combination of `Route` + `RouteHandler`"""

    __slots__ = ("key", "provide", "dependencies")

    def __init__(self, key: str, provide: "Provide", dependencies: List["Dependency"]) -> None:
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


async def resolve_dependency(
    dependency: "Dependency",
    connection: "ASGIConnection",
    kwargs: Dict[str, Any],
    cleanup_group: "DependencyCleanupGroup",
) -> None:
    """Resolve a given instance of [Dependency][starlite.kwargs.Dependency].

    All required sub dependencies must already
    be resolved into the kwargs. The result of the dependency will be stored in the kwargs.

    Args:
        dependency: An instance of [Dependency][starlite.kwargs.Dependency]
        connection: An instance of [Request][starlite.connection.Request] or [WebSocket][starlite.connection.WebSocket].
        kwargs: Any kwargs to pass to the dependency, the result will be stored here as well.
        cleanup_group: DependencyCleanupGroup to which generators returned by `dependency` will be added
    """
    signature_model = get_signature_model(dependency.provide)
    dependency_kwargs = (
        signature_model.parse_values_from_connection_kwargs(connection=connection, **kwargs)
        if signature_model.__fields__
        else {}
    )
    value = await dependency.provide(**dependency_kwargs)

    if isgenerator(value):
        cleanup_group.add(value)
        value = next(value)
    elif isasyncgen(value):
        cleanup_group.add(value)
        value = await async_next(value)

    kwargs[dependency.key] = value


def create_dependency_batches(expected_dependencies: Set["Dependency"]) -> List[Set["Dependency"]]:
    """Calculate batches for all dependencies, recursively.

    Args:
        expected_dependencies: A set of all direct [Dependencies][starlite.kwargs.Dependency].

    Returns:
        A list of batches.
    """
    dependencies_to: Dict["Dependency", Set["Dependency"]] = {}
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
    dependency: "Dependency", dependencies_to: Dict["Dependency", Set["Dependency"]]
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
