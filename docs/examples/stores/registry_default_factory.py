from litestar import Litestar
from litestar.stores.memory import MemoryStore
from litestar.stores.registry import StoreRegistry

memory_store = MemoryStore()


def default_factory(name: str) -> MemoryStore:
    return memory_store


app = Litestar([], stores=StoreRegistry(default_factory=default_factory))
