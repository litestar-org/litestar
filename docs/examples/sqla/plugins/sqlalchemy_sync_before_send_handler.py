from __future__ import annotations

from advanced_alchemy.extensions.litestar import (
    SQLAlchemyInitPlugin,
    SQLAlchemySyncConfig,
    sync_autocommit_before_send_handler,
)

from litestar import Litestar

config = SQLAlchemySyncConfig(
    connection_string="sqlite:///:memory:",
    before_send_handler=sync_autocommit_before_send_handler,
)
plugin = SQLAlchemyInitPlugin(config=config)

app = Litestar(route_handlers=[], plugins=[plugin])
