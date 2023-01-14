from pathlib import Path
from typing import Optional

import pytest
from _pytest.monkeypatch import MonkeyPatch

from starlite import Starlite
from starlite.cli.utils import (
    AUTODISCOVER_PATHS,
    StarliteCLIException,
    StarliteEnv,
    _autodiscover_app,
    _path_to_dotted_path,
)
from tests.cli import (
    APP_FILE_CONTENT,
    CREATE_APP_FILE_CONTENT,
    GENERIC_APP_FACTORY_FILE_CONTENT,
    GENERIC_APP_FACTORY_FILE_CONTENT_STRING_ANNOTATION,
)
from tests.cli.conftest import CreateAppFileFixture


def test_autodiscover_not_found(tmp_project_dir: Path) -> None:
    with pytest.raises(StarliteCLIException):
        _autodiscover_app(None, tmp_project_dir)


@pytest.mark.parametrize("env_name,attr_name", [("STARLITE_DEBUG", "debug"), ("STARLITE_RELOAD", "reload")])
@pytest.mark.parametrize(
    "env_value,expected_value",
    [("true", True), ("True", True), ("1", True), ("0", False), (None, False)],
)
def test_starlite_env_from_env_booleans(
    monkeypatch: MonkeyPatch,
    app_file: Path,
    attr_name: str,
    env_name: str,
    env_value: Optional[str],
    expected_value: bool,
) -> None:
    if env_value is not None:
        monkeypatch.setenv(env_name, env_value)

    env = StarliteEnv.from_env(f"{app_file.stem}:app")

    assert getattr(env, attr_name) is expected_value
    assert isinstance(env.app, Starlite)


def test_starlite_env_from_env_port(monkeypatch: MonkeyPatch, app_file: Path) -> None:
    env = StarliteEnv.from_env(f"{app_file.stem}:app")
    assert env.port is None

    monkeypatch.setenv("STARLITE_PORT", "7000")
    env = StarliteEnv.from_env(f"{app_file.stem}:app")
    assert env.port == 7000


def test_starlite_env_from_env_host(monkeypatch: MonkeyPatch, app_file: Path) -> None:
    env = StarliteEnv.from_env(f"{app_file.stem}:app")
    assert env.host is None

    monkeypatch.setenv("STARLITE_HOST", "0.0.0.0")
    env = StarliteEnv.from_env(f"{app_file.stem}:app")
    assert env.host == "0.0.0.0"


@pytest.mark.parametrize(
    "file_content",
    [
        APP_FILE_CONTENT,
        CREATE_APP_FILE_CONTENT,
        GENERIC_APP_FACTORY_FILE_CONTENT,
        GENERIC_APP_FACTORY_FILE_CONTENT_STRING_ANNOTATION,
    ],
)
@pytest.mark.parametrize("path", AUTODISCOVER_PATHS)
def test_env_from_env_autodiscover_from_files(
    path: str, file_content: str, create_app_file: CreateAppFileFixture
) -> None:
    directory = None
    if "/" in path:
        directory, path = path.split("/", 1)

    tmp_file_path = create_app_file(path, directory, content=file_content)
    env = StarliteEnv.from_env(None)

    assert isinstance(env.app, Starlite)
    assert env.app_path == f"{_path_to_dotted_path(tmp_file_path.relative_to(Path.cwd()))}:app"
