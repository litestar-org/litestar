from __future__ import annotations

from litestar import Litestar
from litestar.contrib.sqlalchemy.plugins import SQLAlchemyInitPlugin, SQLAlchemySyncConfig
from litestar.contrib.sqlalchemy.plugins.init.config.sync import autocommit_before_send_handler

config = SQLAlchemySyncConfig(
    connection_string="sqlite:///:memory:",
    before_send_handler=autocommit_before_send_handler,
)
plugin = SQLAlchemyInitPlugin(config=config)

app = Litestar(route_handlers=[], plugins=[plugin])
