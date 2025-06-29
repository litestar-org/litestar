from __future__ import annotations

from litestar import Litestar
from litestar.plugins.sqlalchemy import (
    SQLAlchemyAsyncConfig,
    SQLAlchemyInitPlugin,
    async_autocommit_before_send_handler,
)

config = SQLAlchemyAsyncConfig(
    connection_string="sqlite+aiosqlite:///:memory:", before_send_handler=async_autocommit_before_send_handler
)
plugin = SQLAlchemyInitPlugin(config=config)

app = Litestar(route_handlers=[], plugins=[plugin])
