from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated, Any, TypeAlias

from litestar.di import Dependency, DependencyKey, DIContext, DIRegistry, Provider
from litestar.di.context import _ProviderSlot

Resolve: TypeAlias = Callable[[DIContext, DependencyKey], Awaitable[Any]]
CallWithDependencies: TypeAlias = Callable[[Callable[..., Awaitable[Any]], list[Provider]], Awaitable[Any]]

ENTRY_POINTS = ("solve", "solve_many", "inject", "solve_arguments")


def registry_with_providers(*providers: Provider) -> DIRegistry:
    return DIRegistry("app", list(providers))


def slot_of(ctx: DIContext, provider: Provider) -> _ProviderSlot:
    """The slot for 'provider'"""
    return ctx._get_or_create_slot_for(provider, ctx.registry.predecessors_of(provider))


async def resolve_through(entry_point: str, ctx: DIContext, key: DependencyKey) -> Any:
    """Resolve 'key' in 'ctx' through 'entry_point'. 'inject' and 'solve_arguments'
    resolve for a target depending on 'key'"""
    if entry_point == "solve":
        return await ctx.solve(key)
    if entry_point == "solve_many":
        return (await ctx.solve_many(key))[0]

    async def target(value: Any) -> Any:
        return value

    # the key is only known at runtime, which a string annotation cannot refer to
    target.__annotations__ = {"value": Annotated[Any, Dependency(key)]}
    if entry_point == "solve_arguments":
        return (await ctx.solve_arguments(target))["value"]
    return await ctx.inject(target)


async def call_with_dependencies_through(
    entry_point: str, fn: Callable[..., Awaitable[Any]], providers: list[Provider]
) -> Any:
    """Call 'fn' with its dependencies resolved from 'providers' in an app context.
    called as an injection target for 'inject' and 'solve_arguments', otherwise as a
    provider resolved through 'entry_point'"""
    if entry_point == "inject":
        async with DIContext(DIRegistry("app", providers)) as ctx:
            return await ctx.inject(fn)
    if entry_point == "solve_arguments":
        async with DIContext(DIRegistry("app", providers)) as ctx:
            return await fn(**await ctx.solve_arguments(fn))

    dependent = Provider(fn, kind="named", key="dependent", scope="app")
    async with DIContext(DIRegistry("app", [*providers, dependent])) as ctx:
        return await resolve_through(entry_point, ctx, "dependent")
