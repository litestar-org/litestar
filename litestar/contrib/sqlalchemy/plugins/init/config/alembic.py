from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from litestar.types import Empty

if TYPE_CHECKING:
    from pathlib import Path

    from litestar.types import EmptyType

__all__ = ("AlembicConfig",)


@dataclass
class AlembicConfig:
    """Configuration for Alembic's :class:`Config <alembic.Config>`.

    For details see: https://docs.sqlalchemy.org/en/20/core/engines.html
    """

    alembic_config: str | Path | EmptyType = Empty
    """A path to the Alembic configuration file such as ``alembic.ini``.  If left unset, the default configuration
    will be used.
    """
    version_table_name: str | EmptyType = Empty
    """Configure the name of the table used to hold the applied alembic revisions. Defaults to ``alembic``.  THe name of the table
    """
    scrip_location: str | Path | EmptyType = Empty
    """A path to save generated migrations.
    """
