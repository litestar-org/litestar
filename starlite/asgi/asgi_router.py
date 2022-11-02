from collections import defaultdict
from traceback import format_exc
from typing import TYPE_CHECKING, Dict, List, Set, Union

from starlite.asgi.routing_trie import validate_node
from starlite.asgi.routing_trie.mapping import add_map_route_to_trie
from starlite.asgi.routing_trie.traversal import parse_scope_to_route
from starlite.asgi.routing_trie.types import create_node
from starlite.asgi.utils import get_route_handlers
from starlite.exceptions import ImproperlyConfiguredException
from starlite.utils import AsyncCallable

if TYPE_CHECKING:
    from starlite.app import Starlite
    from starlite.asgi.routing_trie.types import RouteTrieNode
    from starlite.routes import ASGIRoute, HTTPRoute, WebSocketRoute
    from starlite.routes.base import BaseRoute
    from starlite.types import (
        LifeSpanHandler,
        LifeSpanReceive,
        LifeSpanSend,
        LifeSpanShutdownCompleteEvent,
        LifeSpanShutdownFailedEvent,
        LifeSpanStartupCompleteEvent,
        LifeSpanStartupFailedEvent,
        Receive,
        RouteHandlerType,
        Scope,
        Send,
    )


class ASGIRouter:
    __slots__ = (
        "_plain_routes",
        "_registered_routes",
        "app",
        "root_route_map_node",
        "route_handler_index",
        "route_mapping",
    )

    def __init__(
        self,
        app: "Starlite",
    ) -> None:
        """This class is the Starlite ASGI router. It handles both the ASGI
        lifespan event and routing connection requests.

        Args:
            app: The Starlite app instance
        """
        self._plain_routes: Set[str] = set()
        self._registered_routes: Set[Union["HTTPRoute", "WebSocketRoute", "ASGIRoute"]] = set()
        self.app = app
        self.root_route_map_node: "RouteTrieNode" = create_node()
        self.route_handler_index: Dict[str, "RouteHandlerType"] = {}
        self.route_mapping: Dict[str, List["BaseRoute"]] = defaultdict(list)

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        """The main entry point to the Router class."""
        asgi_app, handler = parse_scope_to_route(
            root_node=self.root_route_map_node, scope=scope, plain_routes=self._plain_routes
        )
        scope["route_handler"] = handler
        await asgi_app(scope, receive, send)

    def _store_handler_to_route_mapping(self, route: "BaseRoute") -> None:
        """Stores the mapping of route handlers to routes and to route handler
        names.

        Args:
            route: A Route instance.

        Returns:
            None
        """

        for handler in get_route_handlers(route):
            if handler.name in self.route_handler_index and str(self.route_handler_index[handler.name]) != str(handler):
                raise ImproperlyConfiguredException(
                    f"route handler names must be unique - {handler.name} is not unique."
                )
            identifier = handler.name or str(handler)
            self.route_mapping[identifier].append(route)
            self.route_handler_index[identifier] = handler

    async def _call_lifespan_handler(self, handler: "LifeSpanHandler") -> None:
        """Determines whether the lifecycle handler expects an argument, and if
        so passes the `app.state` to it. If the handler is an async function,
        it awaits the return.

        Args:
            handler (LifeSpanHandler): sync or async callable that may or may not have an argument.
        """
        async_callable = AsyncCallable(handler)  # type: ignore

        if async_callable.num_expected_args > 0:
            await async_callable(self.app.state)  # type: ignore[arg-type]
        else:
            await async_callable()

    def construct_routing_trie(self) -> None:
        """Create a map of the app's routes.

        This map is used in the asgi router to route requests.
        """
        new_routes = [route for route in self.app.routes if route not in self._registered_routes]
        for route in new_routes:
            node = add_map_route_to_trie(
                root_node=self.root_route_map_node,
                route=route,
                app=self.app,
                plain_routes=self._plain_routes,
            )

            if node["path_parameters"] != route.path_parameters:
                raise ImproperlyConfiguredException("Should not use routes with conflicting path parameters")

            self._store_handler_to_route_mapping(route)
            self._registered_routes.add(route)

        validate_node(node=self.root_route_map_node)

    async def lifespan(self, receive: "LifeSpanReceive", send: "LifeSpanSend") -> None:
        """Handles the ASGI "lifespan" event on application startup and
        shutdown.

        Args:
            receive: The ASGI receive function.
            send: The ASGI send function.

        Returns:
            None.
        """
        message = await receive()
        try:
            shutdown_event: "LifeSpanShutdownCompleteEvent" = {"type": "lifespan.shutdown.complete"}

            if message["type"] == "lifespan.startup":
                await self.startup()
                startup_event: "LifeSpanStartupCompleteEvent" = {"type": "lifespan.startup.complete"}
                await send(startup_event)
                await receive()
            else:
                await self.shutdown()
                await send(shutdown_event)
        except BaseException as e:
            if message["type"] == "lifespan.startup":
                startup_failure_event: "LifeSpanStartupFailedEvent" = {
                    "type": "lifespan.startup.failed",
                    "message": format_exc(),
                }
                await send(startup_failure_event)
            else:
                shutdown_failure_event: "LifeSpanShutdownFailedEvent" = {
                    "type": "lifespan.shutdown.failed",
                    "message": format_exc(),
                }
                await send(shutdown_failure_event)
            raise e
        else:
            await self.shutdown()
            await send(shutdown_event)

    async def startup(self) -> None:
        """Run any [LifeSpanHandlers][starlite.types.LifeSpanHandler] defined
        in the application's `.on_startup` list.

        Calls the `before_startup` hook and `after_startup` hook
        handlers respectively before and after calling in the lifespan
        handlers.
        """
        for hook in self.app.before_startup:
            await hook(self.app)

        for handler in self.app.on_startup:
            await self._call_lifespan_handler(handler)

        for hook in self.app.after_startup:
            await hook(self.app)

    async def shutdown(self) -> None:
        """Run any [LifeSpanHandlers][starlite.types.LifeSpanHandler] defined
        in the application's `.on_shutdown` list.

        Calls the `before_shutdown` hook and `after_shutdown` hook
        handlers respectively before and after calling in the lifespan
        handlers.
        """

        for hook in self.app.before_shutdown:
            await hook(self.app)

        for handler in self.app.on_shutdown:
            await self._call_lifespan_handler(handler)

        for hook in self.app.after_shutdown:
            await hook(self.app)
