from math import inf

from anyio import create_memory_object_stream
from anyio.from_thread import BlockingPortal
from anyio.streams.stapled import StapledObjectStream

from starlite.types import ASGIApp, LifeSpanReceiveMessage, LifeSpanShutdownEvent


class LifeSpanHandler:
    __slots__ = ("stream_send", "stream_receive", "app", "portal", "task")

    def __init__(self, portal: BlockingPortal, app: "ASGIApp"):
        self.app = app
        self.portal = portal
        self.stream_send = StapledObjectStream(*create_memory_object_stream(inf))
        self.stream_receive = StapledObjectStream(*create_memory_object_stream(inf))
        self.task = portal.start_task_soon(self.lifespan)

        portal.call(self.wait_startup)

    async def receive(self) -> LifeSpanReceiveMessage:
        message = await self.stream_send.receive()
        if message is None:
            self.task.result()
        return message

    async def wait_startup(self) -> None:
        await self.stream_receive.send({"type": "lifespan.startup"})

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
