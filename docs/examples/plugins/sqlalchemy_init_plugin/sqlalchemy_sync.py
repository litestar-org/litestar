from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import text

from litestar import Litestar, get
from litestar.plugins.sqlalchemy import SQLAlchemyPlugin, SQLAlchemySyncConfig

if TYPE_CHECKING:
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session


@get(path="/sqlalchemy-app", sync_to_thread=True)
def async_sqlalchemy_init(db_session: Session, db_engine: Engine) -> str:
    """Interact with SQLAlchemy engine and session."""
    one = db_session.execute(text("SELECT 1")).scalar_one()

    with db_engine.connect() as conn:
        two = conn.execute(text("SELECT 2")).scalar_one()

    return f"{one} {two}"


sqlalchemy_config = SQLAlchemySyncConfig(connection_string="sqlite:///test.sqlite")

app = Litestar(
    route_handlers=[async_sqlalchemy_init],
    plugins=[SQLAlchemyPlugin(config=sqlalchemy_config)],
)
