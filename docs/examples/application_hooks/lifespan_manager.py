import asyncio
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from litestar import Litestar


async def worker() -> None:
    while True:
        print(time.time())
        await asyncio.sleep(1)


@asynccontextmanager
async def lifespan(app: Litestar) -> AsyncGenerator[None, None]:
    task = asyncio.create_task(worker())

    try:
        yield
    finally:
        task.cancel()

    await task


app = Litestar(lifespan=[lifespan])
