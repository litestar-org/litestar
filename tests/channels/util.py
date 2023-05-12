from __future__ import annotations

import asyncio

from litestar.channels import Subscriber


async def get_from_stream(subscriber: Subscriber, count: int) -> list[bytes]:
    async def getter() -> list[bytes]:
        items = []
        async for item in subscriber.iter_events():
            items.append(item)
            if len(items) == count:
                break
        return items

    return await asyncio.wait_for(getter(), timeout=1)
