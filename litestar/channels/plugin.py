from __future__ import annotations

import asyncio
from asyncio import CancelledError, Queue, Task, create_task
from contextlib import asynccontextmanager, suppress
from functools import partial
from os.path import join as join_path
from typing import TYPE_CHECKING, AsyncGenerator, Awaitable, Callable, Iterable, NamedTuple

import anyio
import msgspec.json

from litestar.di import Provide
from litestar.exceptions import ImproperlyConfiguredException, LitestarException
from litestar.handlers import WebsocketRouteHandler
from litestar.plugins import InitPluginProtocol
from litestar.serialization import default_serializer

if TYPE_CHECKING:
    from litestar.channels.base import ChannelsBackend
    from litestar.config.app import AppConfig
    from litestar.connection import WebSocket
    from litestar.types import LitestarEncodableType, TypeEncodersMap
    from litestar.types.asgi_types import WebSocketMode


class Subscriber:
    def __init__(self, plugin: ChannelsPlugin) -> None:
        self._queue: Queue[bytes | None] = Queue()
        self._task: asyncio.Task | None = None
        self._plugin = plugin
        self._backend = plugin._backend

    async def put(self, item: bytes | None) -> None:
        await self._queue.put(item)

    def put_nowait(self, item: bytes | None) -> None:
        self._queue.put_nowait(item)

    async def iter_events(self) -> AsyncGenerator[bytes, None]:
        while True:
            item = await self._queue.get()
            if item is None:
                break
            yield item

    async def send_history(self, channels: Iterable[str], limit: int | None = None) -> None:
        async with anyio.create_task_group() as task_group:
            for channel in channels:
                task_group.start_soon(self.send_channel_history, channel, limit)

    async def send_channel_history(self, channel: str, limit: int | None = None) -> None:
        history = await self._backend.get_history(channel, limit)
        for entry in history:
            self._queue.put_nowait(entry)

    @asynccontextmanager
    async def run_in_background(self, socket: WebSocket) -> AsyncGenerator[None, None]:
        self.start_in_background(socket=socket)
        try:
            yield
        finally:
            await self.stop()

    async def _socket_worker(self, socket: WebSocket) -> None:
        handle_send = self._plugin.handle_socket_send
        try:
            async for event in self.iter_events():
                await handle_send(socket, event)
        finally:
            await self._plugin.unsubscribe(self)

    def start_in_background(self, socket: WebSocket) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._socket_worker(socket=socket))

    @property
    def is_running(self) -> bool:
        return self._task is not None

    async def stop(self) -> None:
        if not self._task:
            return

        if not self._task.done():
            self._task.cancel()

        with suppress(CancelledError):
            await self._task

        self._task = None


class ChannelsPlugin(InitPluginProtocol):
    def __init__(
        self,
        backend: ChannelsBackend,
        *,
        channels: Iterable[str] | None = None,
        arbitrary_channels_allowed: bool = False,
        create_route_handlers: bool = False,
        handler_base_path: str = "/",
        socket_send_mode: WebSocketMode = "text",
        type_encoders: TypeEncodersMap | None = None,
        handler_send_history: int = 0,
    ) -> None:
        self._backend = backend
        self._pub_queue: Queue[tuple[bytes, list[str]]] | None = None
        self._pub_task: Task | None = None
        self._sub_task: Task | None = None

        if not (channels or arbitrary_channels_allowed):
            raise ImproperlyConfiguredException("Must define either channels or set arbitrary_channels_allowed=True")

        self._arbitrary_channels_allowed = arbitrary_channels_allowed
        self._create_route_handlers = create_route_handlers
        self._handler_root_path = handler_base_path
        self._socket_send_mode: WebSocketMode = socket_send_mode
        self._encode_json = msgspec.json.Encoder(
            enc_hook=partial(default_serializer, type_encoders=type_encoders)
        ).encode
        self._handler_should_send_history = bool(handler_send_history)
        self._history_limit = None if handler_send_history < 0 else handler_send_history

        self._channels: dict[str, set[Subscriber]] = {channel: set() for channel in channels or []}

    def encode_data(self, data: LitestarEncodableType) -> bytes:
        if isinstance(data, str):
            data = data.encode()
        if isinstance(data, bytes):
            return data
        return self._encode_json(data)

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

    def publish(self, data: LitestarEncodableType, channels: str | Iterable[str]) -> None:
        if isinstance(channels, str):
            channels = [channels]
        data = self.encode_data(data)
        try:
            self._pub_queue.put_nowait((data, list(channels)))  # type: ignore[union-attr]
        except AttributeError as e:
            raise RuntimeError("Plugin not yet initialized. Did you forget to call on_startup?") from e

    async def subscribe(self, channels: str | Iterable[str]) -> Subscriber:
        if isinstance(channels, str):
            channels = [channels]

        subscriber = Subscriber(self)
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

            channel_subscribers.add(subscriber)

        if channels_to_subscribe:
            await self._backend.subscribe(channels_to_subscribe)

        return subscriber

    async def unsubscribe(self, subscriber: Subscriber, channels: str | Iterable[str] | None = None) -> None:
        if channels is None:
            channels = list(self._channels.keys())
        elif isinstance(channels, str):
            channels = [channels]

        channels_to_unsubscribe: set[str] = set()

        for channel in channels:
            channel_subscribers = self._channels[channel]

            try:
                channel_subscribers.remove(subscriber)
            except KeyError:  # subscriber was not subscribed to this channel. This may happen if channels is None
                continue

            if not channel_subscribers:
                del self._channels[channel]
                channels_to_unsubscribe.add(channel)

        if not any(subscriber in queues for queues in self._channels.values()):
            await subscriber.put(None)

        if channels_to_unsubscribe:
            await self._backend.unsubscribe(channels_to_unsubscribe)
        if subscriber.is_running and not any(subscriber in queues for queues in self._channels.values()):
            await subscriber.stop()

    @asynccontextmanager
    async def start_subscription(self, channels: str | Iterable[str]) -> AsyncGenerator[Subscriber, None]:
        subscriber = await self.subscribe(channels)

        try:
            yield subscriber
        finally:
            await self.unsubscribe(subscriber, channels)

    async def _ws_handler_func(self, channel_name: str, socket: WebSocket) -> None:
        await socket.accept()
        async with self.start_subscription(channel_name) as subscriber:
            if self._handler_should_send_history:
                await subscriber.send_channel_history(channel=channel_name, limit=self._history_limit)

            async with subscriber.run_in_background(socket):
                while True:
                    await socket.receive()

    def _create_ws_handler_func(self, channel_name: str) -> Callable[[WebSocket], Awaitable[None]]:
        async def ws_handler_func(socket: WebSocket) -> None:
            await self._ws_handler_func(channel_name=channel_name, socket=socket)

        return ws_handler_func

    async def handle_socket_send(self, socket: WebSocket, data: bytes) -> None:
        await socket.send_data(data, mode=self._socket_send_mode)

    async def _pub_worker(self) -> None:
        while self._pub_queue:
            data, channels = await self._pub_queue.get()
            await self._backend.publish(data, channels)
            self._pub_queue.task_done()

    async def _sub_worker(self) -> None:
        async for channel, payload in self._backend.stream_events():
            for subscriber in self._channels.get(channel, []):
                subscriber.put_nowait(payload)

    async def _on_startup(self) -> None:
        self._pub_queue = Queue()
        self._pub_task = create_task(self._pub_worker())
        self._sub_task = create_task(self._sub_worker())
        await self._backend.on_startup()
        if self._channels:
            await self._backend.subscribe(list(self._channels))

    async def _on_shutdown(self) -> None:
        await asyncio.gather(
            *[
                subscriber.stop()
                for subscribers in self._channels.values()
                for subscriber in subscribers
                if subscriber.is_running
            ]
        )

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
