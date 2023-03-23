from __future__ import annotations

from starlite import Starlite

from .controller import MyController
from .domain import Model

app = Starlite(route_handlers=[MyController], signature_namespace={"Model": Model})
