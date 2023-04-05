from starlite import Starlite
from starlite.stores.memory import MemoryStore
from starlite.stores.registry import StoreRegistry

memory_store = MemoryStore()


def default_factory(name: str) -> MemoryStore:
    return memory_store


app = Starlite([], stores=StoreRegistry(default_factory=default_factory))
