from __future__ import annotations

from pathlib import Path
from typing import Literal, Type

import pytest
from _pytest.monkeypatch import MonkeyPatch
from alembic.util.exc import CommandError

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


@pytest.fixture
def tmp_project_dir(monkeypatch: MonkeyPatch, tmp_path: Path) -> Path:
    path = tmp_path / "project_dir"
    path.mkdir(exist_ok=True)
    monkeypatch.chdir(path)
    return path


def test_sync_alembic_init(sync_alembic_commands: commands.AlembicCommands, tmp_project_dir: Path) -> None:
    sync_alembic_commands.init(directory=f"{tmp_project_dir}/migrations/")
    expected_dirs = [f"{tmp_project_dir}/migrations/", f"{tmp_project_dir}/migrations/versions"]
    expected_files = [f"{tmp_project_dir}/migrations/env.py", f"{tmp_project_dir}/migrations/script.py.mako"]
    for dir in expected_dirs:
        assert Path(dir).is_dir()
    for file in expected_files:
        assert Path(file).is_file()


def test_sync_alembic_init_already(sync_alembic_commands: commands.AlembicCommands, tmp_project_dir: Path) -> None:
    sync_alembic_commands.init(directory=f"{tmp_project_dir}/migrations/")
    expected_dirs = [f"{tmp_project_dir}/migrations/", f"{tmp_project_dir}/migrations/versions"]
    expected_files = [f"{tmp_project_dir}/migrations/env.py", f"{tmp_project_dir}/migrations/script.py.mako"]
    for dir in expected_dirs:
        assert Path(dir).is_dir()
    for file in expected_files:
        assert Path(file).is_file()
    with pytest.raises(CommandError):
        sync_alembic_commands.init(directory=f"{tmp_project_dir}/migrations/")


def test_sync_alembic_revision(sync_alembic_commands: commands.AlembicCommands, tmp_project_dir: Path) -> None:
    sync_alembic_commands.init(directory=f"{tmp_project_dir}/migrations/")
    sync_alembic_commands.revision(message="test", autogenerate=True)


def test_async_alembic_init(async_alembic_commands: commands.AlembicCommands, tmp_project_dir: Path) -> None:
    async_alembic_commands.init(directory=f"{tmp_project_dir}/migrations/")
    expected_dirs = [f"{tmp_project_dir}/migrations/", f"{tmp_project_dir}/migrations/versions"]
    expected_files = [f"{tmp_project_dir}/migrations/env.py", f"{tmp_project_dir}/migrations/script.py.mako"]
    for dir in expected_dirs:
        assert Path(dir).is_dir()
    for file in expected_files:
        assert Path(file).is_file()


def test_async_alembic_init_already(async_alembic_commands: commands.AlembicCommands, tmp_project_dir: Path) -> None:
    async_alembic_commands.init(directory=f"{tmp_project_dir}/migrations/")
    expected_dirs = [f"{tmp_project_dir}/migrations/", f"{tmp_project_dir}/migrations/versions"]
    expected_files = [f"{tmp_project_dir}/migrations/env.py", f"{tmp_project_dir}/migrations/script.py.mako"]
    for dir in expected_dirs:
        assert Path(dir).is_dir()
    for file in expected_files:
        assert Path(file).is_file()
    with pytest.raises(CommandError):
        async_alembic_commands.init(directory=f"{tmp_project_dir}/migrations/")


def test_async_alembic_revision(async_alembic_commands: commands.AlembicCommands, tmp_project_dir: Path) -> None:
    async_alembic_commands.init(directory=f"{tmp_project_dir}/migrations/")
    async_alembic_commands.revision(message="test", autogenerate=True)
