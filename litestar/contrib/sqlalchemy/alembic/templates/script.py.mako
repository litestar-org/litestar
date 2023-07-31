# type: ignore
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
import warnings

import sqlalchemy as sa
from alembic import op
from litestar.contrib.sqlalchemy.types import GUID, ORA_JSONB, DateTimeUTC
${imports if imports else ""}

__all__ = ["downgrade", "upgrade", "schema_upgrades", "schema_downgrades", "data_upgrades", "data_downgrades"]

sa.GUID = GUID
sa.DateTimeUTC = DateTimeUTC
sa.ORA_JSONB = ORA_JSONB

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)
        with op.get_context().autocommit_block():
            schema_upgrades()
            data_upgrades()

def downgrade() -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)
        with op.get_context().autocommit_block():
            data_downgrades()
            schema_downgrades()

def schema_upgrades() -> None:
    """schema upgrade migrations go here."""
    ${upgrades if upgrades else "pass"}

def schema_downgrades() -> None:
    """schema downgrade migrations go here."""
    ${downgrades if downgrades else "pass"}

def data_upgrades() -> None:
    """Add any optional data upgrade migrations here!"""

def data_downgrades() -> None:
    """Add any optional data downgrade migrations here!"""
