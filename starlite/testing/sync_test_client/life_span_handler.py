from typing import TYPE_CHECKING

from starlite.testing.base.life_span_handler_base import BaseLifeSpanHandler

if TYPE_CHECKING:
    from starlite.testing import TestClient
    from starlite.types import LifeSpanReceiveMessage  # noqa: F401  # nopycln: import


class LifeSpanHandler(BaseLifeSpanHandler):
    def __init__(self, client: "TestClient"):
        super().__init__(client=client)
