from asyncio import sleep

from litestar.stores.memory import MemoryStore

store = MemoryStore()


async def main() -> None:
    await store.set("foo", b"bar", expires_in=1)
    await sleep(0.5)

    await store.get(
        "foo", renew_for=1
    )  # this will reset the time to live to one second

    await sleep(1)
    # it has now been 1.5 seconds since the key was set with a life time of one second,
    # so it should have expired however, since it was renewed for one second, it is still available
    value = await store.get("foo")
    print(value)
