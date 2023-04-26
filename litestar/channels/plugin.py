from __future__ import annotations

from asyncio import CancelledError, Queue, Task, create_task
from contextlib import suppress
from functools import partial
from os.path import join as join_path
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Iterable

import anyio
import msgspec.json

from litestar.di import Provide
from litestar.exceptions import ImproperlyConfiguredException, LitestarException, WebSocketDisconnect
from litestar.handlers import WebsocketRouteHandler
from litestar.plugins import InitPluginProtocol
from litestar.serialization import default_serializer

if TYPE_CHECKING:
    from litestar.channels.base import ChannelsBackend
    from litestar.config.app import AppConfig
    from litestar.connection import WebSocket
    from litestar.types import LitestarEncodableType, TypeEncodersMap
    from litestar.types.asgi_types import WebSocketMode


class ChannelsPlugin(InitPluginProtocol):
    def __init__(
        self,
        backend: ChannelsBackend,
        *,
        channels: Iterable[str] | None = None,
        arbitrary_channels_allowed: bool = False,
        create_route_handlers: bool = False,
        handler_base_path: str = "/",
        socket_send_json: bool = True,
        socket_send_mode: WebSocketMode = "text",
        type_encoders: TypeEncodersMap | None = None,
    ) -> None:
        self._backend = backend
        self._pub_queue: Queue[tuple[Any, list[str]]] | None = None
        self._pub_task: Task | None = None
        self._sub_task: Task | None = None

        if not (channels or arbitrary_channels_allowed):
            raise ImproperlyConfiguredException("Must define either channels or set arbitrary_channels_allowed=True")

        self._arbitrary_channels_allowed = arbitrary_channels_allowed
        self._create_route_handlers = create_route_handlers
        self._handler_root_path = handler_base_path
        self._socket_send_json = socket_send_json
        self._socket_send_mode = socket_send_mode
        self._encode_json = msgspec.json.Encoder(
            enc_hook=partial(default_serializer, type_encoders=type_encoders)
        ).encode

        self._channels: dict[str, set[WebSocket]] = {channel: set() for channel in channels or []}

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        app_config.dependencies["channels"] = Provide(lambda: self, use_cache=True)
        app_config.on_startup.append(self._on_startup)
        app_config.on_shutdown.append(self._on_shutdown)

        if self._create_route_handlers:
            if self._arbitrary_channels_allowed:
                path = join_path(self._handler_root_path, "{channel_name:str}")  # noqa: PTH118
                route_handlers = [WebsocketRouteHandler(path)(self._ws_handler_func)]
            else:
                route_handlers = [
                    WebsocketRouteHandler(join_path(self._handler_root_path, channel_name))(  # noqa: PTH118
                        self._create_ws_handler_func(channel_name)
                    )
                    for channel_name in self._channels
                ]
            app_config.route_handlers.extend(route_handlers)

        return app_config

    def broadcast(self, data: LitestarEncodableType, channels: str | list[str]) -> None:
        if isinstance(channels, str):
            channels = [channels]
        if self._pub_queue is None:
            raise RuntimeError()
        self._pub_queue.put_nowait((data, channels))

    async def subscribe(self, socket: WebSocket, channels: str | list[str]) -> None:
        if isinstance(channels, str):
            channels = [channels]

        channels_to_subscribe = set()
        for channel in channels:
            if channel not in self._channels:
                if not self._arbitrary_channels_allowed:
                    raise LitestarException(
                        f"Unknown channel: {channel!r}. Either explicitly defined the channel or set "
                        "arbitrary_channels_allowed=True"
                    )
                self._channels[channel] = set()
            channel_subscribers = self._channels[channel]
            if not channel_subscribers:
                channels_to_subscribe.add(channel)

            channel_subscribers.add(socket)
        if channels_to_subscribe:
            await self._backend.subscribe(channels_to_subscribe)

    async def unsubscribe(self, socket: WebSocket, channels: str | list[str]) -> None:
        if isinstance(channels, str):
            channels = [channels]

        channels_to_unsubscribe = []

        for channel in channels:
            channel_subscribers = self._channels.get(channel) or set()
            channel_subscribers.remove(socket)
            if not channel_subscribers:
                channels_to_unsubscribe.append(channel)

        if channels_to_unsubscribe:
            await self._backend.unsubscribe(channels_to_unsubscribe)

    def get_subscribers(self, channel: str) -> set[WebSocket]:
        return self._channels[channel]

    def get_subscriptions(self, socket: WebSocket) -> set[str]:
        return {channel_name for channel_name, subscribers in self._channels.items() if socket in subscribers}

    async def _ws_handler_func(self, channel_name: str, socket: WebSocket) -> None:
        await socket.accept()
        await self.subscribe(socket, [channel_name])
        while True:
            try:
                await socket.receive()
            except WebSocketDisconnect:
                await self.unsubscribe(socket, [channel_name])
                break

    def _create_ws_handler_func(self, channel_name: str) -> Callable[[WebSocket], Awaitable[None]]:
        async def ws_handler_func(socket: WebSocket) -> None:
            await self._ws_handler_func(channel_name=channel_name, socket=socket)

        return ws_handler_func

    async def handle_socket_send(self, socket: WebSocket, data: Any) -> None:
        if self._socket_send_json:
            data = self._encode_json(data)
        await socket.send_data(data, mode=self._socket_send_mode)

    async def _pub_worker(self) -> None:
        while self._pub_queue:
            data, channels = await self._pub_queue.get()
            await self._backend.publish(data, channels)
            self._pub_queue.task_done()

    async def _sub_worker(self) -> None:
        async with anyio.create_task_group() as task_group:
            async for payload, channels in self._backend.stream_events():
                for channel in channels:
                    for socket in self._channels[channel]:
                        task_group.start_soon(self.handle_socket_send, socket, payload)

    async def _on_startup(self) -> None:
        self._pub_queue = Queue()
        self._pub_task = create_task(self._pub_worker())
        self._sub_task = create_task(self._sub_worker())
        await self._backend.on_startup()

    async def _on_shutdown(self) -> None:
        if self._pub_queue:
            await self._pub_queue.join()
            self._pub_queue = None

        await self._backend.on_shutdown()

        if self._sub_task:
            self._sub_task.cancel()
            with suppress(CancelledError):
                await self._sub_task

        if self._pub_task:
            self._pub_task.cancel()
            with suppress(CancelledError):
                await self._pub_task
