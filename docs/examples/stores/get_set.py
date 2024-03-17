from litestar.stores.memory import MemoryStore

store = MemoryStore()


async def main() -> None:
    value = await store.get("key")
    print(
        value
    )  # this will print 'None', as no store with this key has been defined yet

    await store.set("key", b"value")
    value = await store.get("key")
    print(value)
