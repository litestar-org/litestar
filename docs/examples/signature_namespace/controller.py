from __future__ import annotations

from typing import TYPE_CHECKING

from litestar import Controller, post

if TYPE_CHECKING:
    from .domain import Model


class MyController(Controller):
    @post(sync_to_thread=False)
    def post_handler(self, data: Model) -> Model:
        return data
