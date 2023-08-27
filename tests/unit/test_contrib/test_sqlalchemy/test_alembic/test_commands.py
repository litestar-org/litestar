from __future__ import annotations

from typing import Literal, Type

from litestar.contrib.sqlalchemy.alembic import commands
from litestar.contrib.sqlalchemy.repository import SQLAlchemyAsyncRepository
from tests.unit.test_contrib.test_sqlalchemy import models_uuid

RepositoryPKType = Literal["uuid", "bigint"]
AuthorModel = Type[models_uuid.UUIDAuthor]
RuleModel = Type[models_uuid.UUIDRule]
ModelWithFetchedValue = Type[models_uuid.UUIDModelWithFetchedValue]
ItemModel = Type[models_uuid.UUIDItem]
TagModel = Type[models_uuid.UUIDTag]

AnyAuthor = models_uuid.UUIDAuthor
AuthorRepository = SQLAlchemyAsyncRepository[AnyAuthor]

AnyRule = models_uuid.UUIDRule
RuleRepository = SQLAlchemyAsyncRepository[AnyRule]

AnyBook = models_uuid.UUIDBook
BookRepository = SQLAlchemyAsyncRepository[AnyBook]

AnyTag = models_uuid.UUIDTag
TagRepository = SQLAlchemyAsyncRepository[AnyTag]

AnyItem = models_uuid.UUIDItem
ItemRepository = SQLAlchemyAsyncRepository[AnyItem]

AnyModelWithFetchedValue = models_uuid.UUIDModelWithFetchedValue
ModelWithFetchedValueRepository = SQLAlchemyAsyncRepository[AnyModelWithFetchedValue]


def test_sync_alembic_init(sync_alembic_commands: commands.AlembicCommands) -> None:
    sync_alembic_commands.init(directory="./migrations/")


def test_async_alembic_init(async_alembic_commands: commands.AlembicCommands) -> None:
    async_alembic_commands.init(directory="./migrations/")
