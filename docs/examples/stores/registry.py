from litestar import Litestar
from litestar.stores.memory import MemoryStore

app = Litestar([], stores={"memory": MemoryStore()})

memory_store = app.stores.get("memory")
# this is the previously defined store

some_other_store = app.stores.get("something_else")
# this will be a newly created instance

assert app.stores.get("something_else") is some_other_store
# but subsequent requests will return the same instance
