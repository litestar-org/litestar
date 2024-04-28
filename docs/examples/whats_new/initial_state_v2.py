from litestar import Litestar
from litestar.datastructures import State

app = Litestar(..., state=State({"some": "key"}))
