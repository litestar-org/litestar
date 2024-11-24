from __future__ import annotations

import warnings
from math import inf
from typing import TYPE_CHECKING, Generic, Optional, TypeVar, cast

from anyio import create_memory_object_stream
from anyio.streams.stapled import StapledObjectStream

from litestar.testing.client.base import BaseTestClient

if TYPE_CHECKING:
    from types import TracebackType

    from litestar.types import (
        LifeSpanReceiveMessage,  # noqa: F401
        LifeSpanSendMessage,
        LifeSpanShutdownEvent,
        LifeSpanStartupEvent,
    )

T = TypeVar("T", bound=BaseTestClient)


class LifeSpanHandler(Generic[T]):
    __slots__ = (
        "_startup_done",
        "client",
        "stream_receive",
        "stream_send",
        "task",
    )

    def __init__(self, client: T) -> None:
        self.client = client
        self.stream_send = StapledObjectStream[Optional["LifeSpanSendMessage"]](*create_memory_object_stream(inf))  # type: ignore[arg-type]
        self.stream_receive = StapledObjectStream["LifeSpanReceiveMessage"](*create_memory_object_stream(inf))  # type: ignore[arg-type]
        self._startup_done = False

    def _ensure_setup(self, is_safe: bool = False) -> None:
        if self._startup_done:
            return

        if not is_safe:
            warnings.warn(
                "LifeSpanHandler used with implicit startup; Use LifeSpanHandler as a context manager instead. "
                "Implicit startup will be deprecated in version 3.0.",
                category=DeprecationWarning,
                stacklevel=2,
            )

        self._startup_done = True
        with self.client.portal() as portal:
            self.task = portal.start_task_soon(self.lifespan)
            portal.call(self.wait_startup)

    def close(self) -> None:
        with self.client.portal() as portal:
            portal.call(self.stream_send.aclose)
            portal.call(self.stream_receive.aclose)

    def __enter__(self) -> LifeSpanHandler:
        try:
            self._ensure_setup(is_safe=True)
        except Exception as exc:
            self.close()
            raise exc
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    async def receive(self) -> LifeSpanSendMessage:
        self._ensure_setup()

        message = await self.stream_send.receive()
        if message is None:
            self.task.result()
        return cast("LifeSpanSendMessage", message)

    async def wait_startup(self) -> None:
        self._ensure_setup()

        event: LifeSpanStartupEvent = {"type": "lifespan.startup"}
        await self.stream_receive.send(event)

        message = await self.receive()
        if message["type"] not in (
            "lifespan.startup.complete",
            "lifespan.startup.failed",
        ):
            raise RuntimeError(
                "Received unexpected ASGI message type. Expected 'lifespan.startup.complete' or "
                f"'lifespan.startup.failed'. Got {message['type']!r}",
            )
        if message["type"] == "lifespan.startup.failed":
            await self.receive()

    async def wait_shutdown(self) -> None:
        self._ensure_setup()

        async with self.stream_send:
            lifespan_shutdown_event: LifeSpanShutdownEvent = {"type": "lifespan.shutdown"}
            await self.stream_receive.send(lifespan_shutdown_event)

            message = await self.receive()
            if message["type"] not in (
                "lifespan.shutdown.complete",
                "lifespan.shutdown.failed",
            ):
                raise RuntimeError(
                    "Received unexpected ASGI message type. Expected 'lifespan.shutdown.complete' or "
                    f"'lifespan.shutdown.failed'. Got {message['type']!r}",
                )
            if message["type"] == "lifespan.shutdown.failed":
                await self.receive()

    async def lifespan(self) -> None:
        self._ensure_setup()

        scope = {"type": "lifespan"}
        try:
            await self.client.app(scope, self.stream_receive.receive, self.stream_send.send)
        finally:
            await self.stream_send.send(None)
