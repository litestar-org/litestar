from asyncio import sleep

from litestar.stores.memory import MemoryStore

store = MemoryStore()


async def main() -> None:
    await store.set("foo", b"bar", expires_in=1)
    value = await store.get("foo")
    print(value)

    await sleep(1)
    value = await store.get("foo")  # this will return 'None', since the key has expired
    print(value)
