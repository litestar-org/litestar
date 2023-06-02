from __future__ import annotations

from litestar import Litestar
from litestar.contrib.sqlalchemy.plugins import SQLAlchemyAsyncConfig, SQLAlchemyInitPlugin
from litestar.contrib.sqlalchemy.plugins.init.config.asyncio import autocommit_before_send_handler

config = SQLAlchemyAsyncConfig(
    connection_string="sqlite+aiosqlite:///:memory:",
    before_send_handler=autocommit_before_send_handler,
)
plugin = SQLAlchemyInitPlugin(config=config)

app = Litestar(route_handlers=[], plugins=[plugin])
