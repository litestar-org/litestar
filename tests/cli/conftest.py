from pathlib import Path
from shutil import rmtree
from typing import TYPE_CHECKING, Callable, Generator, List, Optional, Protocol, Union

import pytest
from _pytest.fixtures import FixtureRequest
from _pytest.monkeypatch import MonkeyPatch
from click.testing import CliRunner
from pytest_mock import MockerFixture

from tests.cli import APP_FILE_CONTENT

if TYPE_CHECKING:
    from unittest.mock import MagicMock


@pytest.fixture
def patch_autodiscovery_paths(request: FixtureRequest) -> Callable[[List[str]], None]:
    def patcher(paths: List[str]) -> None:
        from starlite.cli.utils import AUTODISCOVER_PATHS

        old_paths = AUTODISCOVER_PATHS[::]
        AUTODISCOVER_PATHS[:] = paths

        def finalizer() -> None:
            AUTODISCOVER_PATHS[:] = old_paths

        request.addfinalizer(finalizer)

    return patcher


@pytest.fixture
def tmp_project_dir(monkeypatch: MonkeyPatch, tmp_path: Path) -> Path:
    path = tmp_path / "project_dir"
    path.mkdir(exist_ok=True)
    monkeypatch.chdir(path)
    return path


class CreateAppFileFixture(Protocol):
    def __call__(
        self,
        file: Union[str, Path],
        directory: Optional[Union[str, Path]] = None,
        content: Optional[str] = None,
    ) -> Path:
        ...


@pytest.fixture
def create_app_file(
    tmp_project_dir: Path,
    request: FixtureRequest,
) -> CreateAppFileFixture:
    def _create_app_file(
        file: Union[str, Path],
        directory: Optional[Union[str, Path]] = None,
        content: Optional[str] = None,
    ) -> Path:
        base = tmp_project_dir
        if directory:
            base /= directory
            base.mkdir()

        tmp_app_file = base / file
        tmp_app_file.write_text(content or APP_FILE_CONTENT)

        if directory:
            request.addfinalizer(lambda: rmtree(directory))  # type: ignore[arg-type]
        else:
            request.addfinalizer(tmp_app_file.unlink)
        return tmp_app_file

    return _create_app_file


@pytest.fixture
def app_file(create_app_file: CreateAppFileFixture) -> Path:
    return create_app_file("asgi.py")


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def mock_subprocess_run(mocker: MockerFixture) -> "MagicMock":
    return mocker.patch("subprocess.run")


@pytest.fixture
def mock_confirm_ask(mocker: MockerFixture) -> Generator["MagicMock", None, None]:
    yield mocker.patch("rich.prompt.Confirm.ask", return_value=True)
