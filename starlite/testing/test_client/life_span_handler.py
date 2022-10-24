from math import inf
from typing import TYPE_CHECKING, Optional, cast

from anyio import create_memory_object_stream
from anyio.streams.stapled import StapledObjectStream

if TYPE_CHECKING:
    from anyio.from_thread import BlockingPortal

    from starlite.types import LifeSpanReceiveMessage  # noqa: F401  # nopycln: import
    from starlite.types import (
        ASGIApp,
        LifeSpanSendMessage,
        LifeSpanShutdownEvent,
        LifeSpanStartupEvent,
    )


class LifeSpanHandler:
    __slots__ = ("stream_send", "stream_receive", "app", "portal", "task")

    def __init__(self, portal: "BlockingPortal", app: "ASGIApp"):
        self.app = app
        self.portal = portal
        self.stream_send = StapledObjectStream[Optional["LifeSpanSendMessage"]](*create_memory_object_stream(inf))
        self.stream_receive = StapledObjectStream["LifeSpanReceiveMessage"](*create_memory_object_stream(inf))
        self.task = portal.start_task_soon(self.lifespan)

        portal.call(self.wait_startup)

    async def receive(self) -> "LifeSpanSendMessage":
        message = await self.stream_send.receive()
        if message is None:
            self.task.result()
        return cast("LifeSpanSendMessage", message)

    async def wait_startup(self) -> None:
        event: "LifeSpanStartupEvent" = {"type": "lifespan.startup"}
        await self.stream_receive.send(event)

        message = await self.receive()
        assert message["type"] in (
            "lifespan.startup.complete",
            "lifespan.startup.failed",
        )
        if message["type"] == "lifespan.startup.failed":
            await self.receive()

    async def wait_shutdown(self) -> None:
        async with self.stream_send:
            lifespan_shutdown_event: "LifeSpanShutdownEvent" = {"type": "lifespan.shutdown"}
            await self.stream_receive.send(lifespan_shutdown_event)

            message = await self.receive()
            assert message["type"] in (
                "lifespan.shutdown.complete",
                "lifespan.shutdown.failed",
            )
            if message["type"] == "lifespan.shutdown.failed":
                await self.receive()

    async def lifespan(self) -> None:
        scope = {"type": "lifespan"}
        try:
            await self.app(scope, self.stream_receive.receive, self.stream_send.send)  # type: ignore
        finally:
            await self.stream_send.send(None)
