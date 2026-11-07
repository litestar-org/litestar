from __future__ import annotations

from typing import TYPE_CHECKING

from advanced_alchemy.extensions.litestar import SQLAlchemyInitPlugin, SQLAlchemySyncConfig
from sqlalchemy import literal, select

from litestar import Litestar, post
from litestar.di import NamedDependency

if TYPE_CHECKING:
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session


@post("/", sync_to_thread=True)
def handler(db_session: NamedDependency[Session], db_engine: NamedDependency[Engine]) -> tuple[int, int]:
    one = db_session.scalars(select(literal(1))).one()

    with db_engine.begin() as conn:
        two = conn.scalars(select(literal(2))).one()

    return one, two


config = SQLAlchemySyncConfig(connection_string="sqlite:///sync.sqlite")
plugin = SQLAlchemyInitPlugin(config=config)
app = Litestar(route_handlers=[handler], plugins=[plugin])
