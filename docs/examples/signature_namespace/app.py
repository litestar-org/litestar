from __future__ import annotations

from litestar import Litestar

from .controller import MyController
from .domain import Model

app = Litestar(route_handlers=[MyController], signature_types=[Model])
