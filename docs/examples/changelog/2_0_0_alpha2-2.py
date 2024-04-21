from starlite import Starlite
from starlite.datastructures.state import State

app = Starlite(..., state=State({"some": "key"}))