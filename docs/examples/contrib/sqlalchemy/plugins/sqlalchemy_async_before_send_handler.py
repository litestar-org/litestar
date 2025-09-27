from __future__ import annotations

from advanced_alchemy.extensions.litestar import (
    SQLAlchemyAsyncConfig,
    SQLAlchemyInitPlugin,
    async_autocommit_before_send_handler,
)

from litestar import Litestar

config = SQLAlchemyAsyncConfig(
    connection_string="sqlite+aiosqlite:///:memory:", before_send_handler=async_autocommit_before_send_handler
)
plugin = SQLAlchemyInitPlugin(config=config)

app = Litestar(route_handlers=[], plugins=[plugin])
