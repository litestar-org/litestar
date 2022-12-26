from typing import TYPE_CHECKING

from starlite.testing.base.life_span_handler_base import BaseLifeSpanHandler

if TYPE_CHECKING:
    from starlite.testing import AsyncTestClient
    from starlite.types import LifeSpanReceiveMessage  # noqa: F401  # nopycln: import


class LifeSpanHandler(BaseLifeSpanHandler):
    def __init__(self, client: "AsyncTestClient"):
        super().__init__(client=client)
