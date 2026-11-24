from __future__ import annotations

import asyncio
import re
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from litestar.handlers import ASGIRouteHandler
    from litestar.routes import ASGIRoute, HTTPRoute, WebSocketRoute
    from litestar.routes.base import BaseRoute
    from litestar.types import ASGIApp, LifeSpanReceiveMessage, LifeSpanSendMessage, RouteHandlerType

__all__ = (
    "get_route_handlers",
    "is_valid_host",
    "run_asgi_lifespan",
    "wrap_in_exception_handler",
)

_HOST_HEADER_REGEX = re.compile(
    rb"\A[0-9A-Za-z!$&'()*+,;=\-._~:\[\]@%]*\Z",
    re.IGNORECASE,
)


def is_valid_host(host: bytes) -> bool:
    return _HOST_HEADER_REGEX.match(host) is not None


def wrap_in_exception_handler(app: ASGIApp) -> ASGIApp:
    """Wrap the given ASGIApp in an instance of ExceptionHandlerMiddleware.

    Args:
        app: The ASGI app that is being wrapped.

    Returns:
        A wrapped ASGIApp.
    """
    from litestar.middleware._internal.exceptions import ExceptionHandlerMiddleware

    return ExceptionHandlerMiddleware(app=app)


def get_route_handlers(route: BaseRoute) -> list[RouteHandlerType]:
    """Retrieve handler(s) as a list for given route.

    Args:
        route: The route from which the route handlers are extracted.

    Returns:
        The route handlers defined on the route.
    """
    route_handlers: list[RouteHandlerType] = []
    if hasattr(route, "route_handlers"):
        route_handlers.extend(cast("HTTPRoute", route).route_handlers)
    else:
        route_handlers.append(cast("WebSocketRoute | ASGIRoute", route).route_handler)

    return route_handlers


@asynccontextmanager
async def run_asgi_lifespan(handler: ASGIRouteHandler) -> AsyncGenerator[None, None]:
    """Run the ASGI lifespan of a mounted ASGI handler"""
    to_app: asyncio.Queue[LifeSpanReceiveMessage] = asyncio.Queue()
    from_app: asyncio.Queue[LifeSpanSendMessage | None] = asyncio.Queue()

    async def call_app() -> None:
        try:
            await handler.fn(
                scope={
                    "type": "lifespan",
                    "asgi": {"version": "3.0", "spec_version": "2.0"},
                    "state": handler._lifespan_state,
                },
                receive=to_app.get,
                send=from_app.put,
            )
        finally:
            from_app.put_nowait(None)

    async def exchange(event: LifeSpanReceiveMessage) -> None:
        to_app.put_nowait(event)
        message = await from_app.get()
        if message is not None and message["type"] == f"{event['type']}.complete":
            return

        # an app that raises right after sending the failure has raised by now: 'send' never suspends
        task.cancel()
        await asyncio.wait([task])
        if not task.cancelled() and (exception := task.exception()) is not None:
            raise exception

        if message is None:
            answer = f"returned without sending '{event['type']}.complete'"
        elif message["type"] == f"{event['type']}.failed":
            answer = f"sent {message['type']!r}: {message.get('message', '')}"
        else:
            answer = f"sent {message['type']!r}"
        paths = ",".join(sorted(handler.paths))
        raise RuntimeError(f"[paths={paths!r}, handler={str(handler)!r}] on {event['type']!r} the ASGI app {answer}")

    task = asyncio.create_task(call_app())
    try:
        await exchange({"type": "lifespan.startup"})
        try:
            yield
        finally:
            await exchange({"type": "lifespan.shutdown"})
    finally:
        handler._lifespan_state.clear()
        task.cancel()
        await asyncio.wait([task])
