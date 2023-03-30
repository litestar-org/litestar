from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import text

from starlite import Starlite, get
from starlite.contrib.sqlalchemy.init_plugin import SQLAlchemyInitPlugin, SQLAlchemySyncConfig

if TYPE_CHECKING:
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session


@get(path="/sqlalchemy-app")
def async_sqlalchemy_init(db_session: Session, db_engine: Engine) -> str:
    """Interact with SQLAlchemy engine and session."""
    one = db_session.execute(text("SELECT 1")).scalar_one()

    with db_engine.connect() as conn:
        two = conn.execute(text("SELECT 2")).scalar_one()

    return f"{one} {two}"


sqlalchemy_config = SQLAlchemySyncConfig(connection_string="sqlite:///test.sqlite")

app = Starlite(
    route_handlers=[async_sqlalchemy_init],
    plugins=[SQLAlchemyInitPlugin(config=sqlalchemy_config)],
)
