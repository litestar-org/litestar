from __future__ import annotations

import contextlib
from math import inf
from typing import TYPE_CHECKING, Optional, cast

import anyio
from anyio import create_memory_object_stream
from anyio.streams.stapled import StapledObjectStream

if TYPE_CHECKING:
    from types import TracebackType

    from litestar.types import (
        ASGIApp,
        LifeSpanReceiveMessage,  # noqa: F401
        LifeSpanSendMessage,
        LifeSpanShutdownEvent,
        LifeSpanStartupEvent,
    )


class LifeSpanHandler:
    def __init__(self, app: ASGIApp) -> None:
        self.stream_send = StapledObjectStream[Optional["LifeSpanSendMessage"]](*create_memory_object_stream(inf))  # type: ignore[arg-type]
        self.stream_receive = StapledObjectStream["LifeSpanReceiveMessage"](*create_memory_object_stream(inf))  # type: ignore[arg-type]
        self.app = app
        self._lifespan_finished = anyio.Event()
        self._exit_stack = contextlib.AsyncExitStack()

    async def __aenter__(self) -> LifeSpanHandler:
        async with contextlib.AsyncExitStack() as exit_stack:
            await exit_stack.enter_async_context(self.stream_send)
            await exit_stack.enter_async_context(self.stream_receive)

            self._tg = await exit_stack.enter_async_context(anyio.create_task_group())
            with anyio.CancelScope() as cs:
                self._tg.start_soon(self.lifespan, cs)
                await self.wait_startup()
            exit_stack.push_async_callback(self.wait_shutdown)

            self._lifespan_finished.set()
            self._exit_stack = exit_stack.pop_all()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self._exit_stack.__aexit__(exc_type, exc_value, traceback)

    async def receive(self) -> LifeSpanSendMessage:
        message = await self.stream_send.receive()
        if message is None:
            await self._lifespan_finished.wait()
        return cast("LifeSpanSendMessage", message)

    async def wait_startup(self) -> None:
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

    async def lifespan(self, cs: anyio.CancelScope) -> None:
        scope = {"type": "lifespan"}
        try:
            await self.app(scope, self.stream_receive.receive, self.stream_send.send)  # type: ignore[arg-type]
        except BaseException:
            cs.cancel()
            raise
