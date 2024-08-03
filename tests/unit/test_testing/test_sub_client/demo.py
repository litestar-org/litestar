"""
Assemble components into an app that shall be tested
"""

from typing import AsyncIterator

from redis.asyncio import Redis

from litestar import Litestar, get
from litestar.channels import ChannelsPlugin
from litestar.channels.backends.redis import RedisChannelsPubSubBackend
from litestar.response import ServerSentEvent


@get("/notify/{topic:str}")
async def get_notified(topic: str, channels: ChannelsPlugin) -> ServerSentEvent:
    async def generator() -> AsyncIterator[bytes]:
        async with channels.start_subscription([topic]) as subscriber:
            async for event in subscriber.iter_events():
                yield event

    return ServerSentEvent(generator(), event_type="Notifier")


def create_test_app() -> Litestar:
    redis_instance = Redis()
    channels_backend = RedisChannelsPubSubBackend(redis=redis_instance)
    channels_instance = ChannelsPlugin(backend=channels_backend, arbitrary_channels_allowed=True)

    return Litestar(
        route_handlers=[
            get_notified,
        ],
        plugins=[channels_instance],
    )


app = create_test_app()
