from alembic import command as migration_command
from alembic.config import Config as AlembicConfig
from sqlalchemy import Table
from sqlalchemy.schema import DropTable

from spannermc.lib import log, settings

from .base import engine
from .orm import DatabaseModel, orm_registry

__all__ = [
    "create_database",
    "drop_tables",
    "purge_database",
    "reset_database",
    "show_database_revision",
    "upgrade_database",
]


logger = log.get_logger()


async def create_database() -> None:
    """Create database DDL migrations."""
    alembic_cfg = AlembicConfig(settings.db.MIGRATION_CONFIG)
    alembic_cfg.set_main_option("script_location", settings.db.MIGRATION_PATH)
    migration_command.upgrade(alembic_cfg, "head")


async def upgrade_database() -> None:
    """Upgrade the database to the latest revision."""
    alembic_cfg = AlembicConfig(settings.db.MIGRATION_CONFIG)
    alembic_cfg.set_main_option("script_location", settings.db.MIGRATION_PATH)
    migration_command.upgrade(alembic_cfg, "head")


async def reset_database() -> None:
    """Reset the database to an initial empty state."""
    alembic_cfg = AlembicConfig(settings.db.MIGRATION_CONFIG)
    alembic_cfg.set_main_option("script_location", settings.db.MIGRATION_PATH)
    drop_tables()
    migration_command.upgrade(alembic_cfg, "head")


async def purge_database() -> None:
    """Drop all objects in the database."""
    alembic_cfg = AlembicConfig(settings.db.MIGRATION_CONFIG)
    alembic_cfg.set_main_option("script_location", settings.db.MIGRATION_PATH)
    drop_tables()


async def show_database_revision() -> None:
    """Show current database revision."""
    alembic_cfg = AlembicConfig(settings.db.MIGRATION_CONFIG)
    alembic_cfg.set_main_option("script_location", settings.db.MIGRATION_PATH)
    migration_command.current(alembic_cfg, verbose=False)


def drop_tables() -> None:
    """Drop all tables from the database."""
    logger.info("Connecting to database backend.")
    with engine.begin() as db:
        logger.info("Dropping the db")
        DatabaseModel.metadata.drop_all(db)
        logger.info("Dropping the version table")
        db.execute(
            DropTable(
                element=Table(settings.db.MIGRATION_DDL_VERSION_TABLE, orm_registry.metadata),
                if_exists=True,
            ),
        )
        db.commit()
    logger.info("Successfully dropped all objects")
