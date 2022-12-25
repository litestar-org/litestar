import re
from collections import defaultdict
from functools import lru_cache
from traceback import format_exc
from typing import TYPE_CHECKING, Dict, List, Optional, Pattern, Set, Tuple, Union

from starlite.asgi.routing_trie import validate_node
from starlite.asgi.routing_trie.mapping import add_route_to_trie
from starlite.asgi.routing_trie.traversal import parse_path_to_route
from starlite.asgi.routing_trie.types import create_node
from starlite.asgi.utils import get_route_handlers
from starlite.exceptions import ImproperlyConfiguredException
from starlite.utils import AsyncCallable, normalize_path

if TYPE_CHECKING:
    from starlite.app import Starlite
    from starlite.asgi.routing_trie.types import RouteTrieNode
    from starlite.routes import ASGIRoute, HTTPRoute, WebSocketRoute
    from starlite.routes.base import BaseRoute
    from starlite.types import (
        ASGIApp,
        LifeSpanHandler,
        LifeSpanReceive,
        LifeSpanSend,
        LifeSpanShutdownCompleteEvent,
        LifeSpanShutdownFailedEvent,
        LifeSpanStartupCompleteEvent,
        LifeSpanStartupFailedEvent,
        Method,
        Receive,
        RouteHandlerType,
        Scope,
        Send,
    )


class ASGIRouter:
    """Starlite ASGI router.

    Handling both the ASGI lifespan events and routing of connection requests.
    """

    __slots__ = (
        "_mount_paths_regex",
        "_mount_routes",
        "_plain_routes",
        "_registered_routes",
        "_static_routes",
        "app",
        "root_route_map_node",
        "route_handler_index",
        "route_mapping",
    )

    def __init__(self, app: "Starlite") -> None:
        """Initialize `ASGIRouter`.

        Args:
            app: The Starlite app instance
        """
        self._mount_paths_regex: Optional[Pattern] = None
        self._mount_routes: Dict[str, "RouteTrieNode"] = {}
        self._plain_routes: Set[str] = set()
        self._registered_routes: Set[Union["HTTPRoute", "WebSocketRoute", "ASGIRoute"]] = set()
        self.app = app
        self.root_route_map_node: "RouteTrieNode" = create_node()
        self.route_handler_index: Dict[str, "RouteHandlerType"] = {}
        self.route_mapping: Dict[str, List["BaseRoute"]] = defaultdict(list)

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        """ASGI callable.

        The main entry point to the Router class.
        """
        scope.setdefault("path_params", {})
        normalized_path = normalize_path(scope["path"])
        asgi_app, scope["route_handler"], scope["path"], scope["path_params"] = self.handle_routing(
            path=normalized_path, method=scope.get("method")
        )
        await asgi_app(scope, receive, send)

    @lru_cache(1024)  # noqa: B019
    def handle_routing(self, path: str, method: Optional["Method"]) -> Tuple["ASGIApp", "RouteHandlerType", str, dict]:
        """Handle routing for a given path / method combo. This method is meant to allow easy caching.

        Args:
            path: The path of the request.
            method: The scope's method, if any.

        Returns:
            A tuple composed of the ASGIApp of the route, the route handler instance, the resolved and normalized path and any parsed path params.
        """
        return parse_path_to_route(
            mount_paths_regex=self._mount_paths_regex,
            mount_routes=self._mount_routes,
            path=path,
            plain_routes=self._plain_routes,
            root_node=self.root_route_map_node,
            method=method,
        )

    def _store_handler_to_route_mapping(self, route: "BaseRoute") -> None:
        """Store the mapping of route handlers to routes and to route handler names.

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
        """Determine whether the lifecycle handler expects an argument, and if so pass the `app.state` to it. If the
        handler is an async function, await the return.

        Args:
            handler: sync or async callable that may or may not have an argument.
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
            add_route_to_trie(
                app=self.app,
                mount_routes=self._mount_routes,
                plain_routes=self._plain_routes,
                root_node=self.root_route_map_node,
                route=route,
            )
            self._store_handler_to_route_mapping(route)
            self._registered_routes.add(route)

        validate_node(node=self.root_route_map_node)
        if self._mount_routes:
            self._mount_paths_regex = re.compile("|".join(sorted(set(self._mount_routes))))

    async def lifespan(self, receive: "LifeSpanReceive", send: "LifeSpanSend") -> None:
        """Handle the ASGI "lifespan" event on application startup and shutdown.

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
        """Run any [LifeSpanHandlers][starlite.types.LifeSpanHandler] defined in the application's `.on_startup` list.

        Calls the `before_startup` hook and `after_startup` hook handlers respectively before and after calling in the
        lifespan handlers.
        """
        for hook in self.app.before_startup:
            await hook(self.app)

        for handler in self.app.on_startup:
            await self._call_lifespan_handler(handler)

        for hook in self.app.after_startup:
            await hook(self.app)

    async def shutdown(self) -> None:
        """Run any [LifeSpanHandlers][starlite.types.LifeSpanHandler] defined in the application's `.on_shutdown` list.

        Calls the `before_shutdown` hook and `after_shutdown` hook handlers respectively before and after calling in the
        lifespan handlers.
        """
        for hook in self.app.before_shutdown:
            await hook(self.app)

        for handler in self.app.on_shutdown:
            await self._call_lifespan_handler(handler)

        for hook in self.app.after_shutdown:
            await hook(self.app)
