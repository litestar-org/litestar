#  TODO
#   Without --create-devcert
#       Test run with actual certs?
#   With --create-devcert
#       Test either file parent dir doesn't exist
#       Test both filepaths are valid
from pathlib import Path
from typing import Optional, Protocol, cast

import pytest
from click import ClickException
from click.testing import CliRunner
from pytest_mock import MockerFixture

from litestar.cli.main import litestar_group as cli_command


class GetClickExceptionFixture(Protocol):
    def __call__(self, exception: SystemExit) -> ClickException:
        ...


@pytest.fixture
def get_click_exception() -> GetClickExceptionFixture:
    def _get_click_exception(exception: SystemExit) -> ClickException:
        exc = exception
        while exc.__context__ is not None:
            if isinstance(exc, ClickException):
                break
            exc = exc.__context__
        return cast(ClickException, exc)

    return _get_click_exception


@pytest.mark.parametrize("create_devcert", (True, False))
@pytest.mark.usefixtures("mock_uvicorn_run")
def test_both_files_provided(app_file: Path, runner: CliRunner, create_devcert: bool) -> None:
    path = app_file
    app_path = f"{path.stem}:app"

    cert_path = path.parent / "cert.pem"
    cert_path.touch()

    key_path = path.parent / "key.pem"
    key_path.touch()

    args = ["--app", app_path, "run", "--ssl-certfile", str(cert_path), "--ssl-keyfile", str(key_path)]

    if create_devcert:
        args.append("--create-devcert")

    result = runner.invoke(cli_command, args)

    assert result.exception is None
    assert result.exit_code == 0


@pytest.mark.parametrize("create_devcert", (True, False))
@pytest.mark.parametrize(
    "ssl_certfile, ssl_keyfile",
    [("directory", "exists.pem"), ("exists.pem", "directory")],
)
def test_path_is_a_directory(
    app_file: Path,
    runner: CliRunner,
    ssl_certfile: Optional[str],
    ssl_keyfile: Optional[str],
    create_devcert: bool,
    get_click_exception: GetClickExceptionFixture,
) -> None:
    path = app_file
    app_path = f"{path.stem}:app"

    (path.parent / "exists.pem").touch()
    (path.parent / "directory").mkdir(exist_ok=True)

    args = ["--app", app_path, "run", "--ssl-certfile", str(ssl_certfile), "--ssl-keyfile", str(ssl_keyfile)]

    if create_devcert:
        args.append("--create-devcert")

    result = runner.invoke(cli_command, args)

    assert result.exit_code == 1

    assert isinstance(result.exception, SystemExit)
    exc = get_click_exception(result.exception)
    assert "Provided path is a directory" in exc.message


@pytest.mark.parametrize(
    "ssl_certfile, ssl_keyfile",
    [("exists.pem", None), ("exists.pem", "not_exists.pem"), (None, "exists.pem"), ("not_exists.pem", "exists.pem")],
)
def test_one_file_provided(
    app_file: Path,
    runner: CliRunner,
    ssl_certfile: Optional[str],
    ssl_keyfile: Optional[str],
    get_click_exception: GetClickExceptionFixture,
) -> None:
    path = app_file
    app_path = f"{path.stem}:app"

    (path.parent / "exists.pem").touch()

    args = ["--app", app_path, "run", "--ssl-certfile", str(ssl_certfile), "--ssl-keyfile", str(ssl_keyfile)]

    result = runner.invoke(cli_command, args)

    assert result.exit_code == 1

    assert isinstance(result.exception, SystemExit)
    exc = get_click_exception(result.exception)
    assert "file path is invalid or was not provided" in exc.message


@pytest.mark.parametrize(
    "ssl_certfile, ssl_keyfile",
    [(None, "exists.pem"), ("exists.pem", None), ("not_exists.pem", "exists.pem"), ("exists.pem", "not_exists.pem")],
)
def test_one_file_found(
    app_file: Path,
    runner: CliRunner,
    ssl_certfile: Optional[str],
    ssl_keyfile: Optional[str],
    get_click_exception: GetClickExceptionFixture,
) -> None:
    path = app_file
    app_path = f"{path.stem}:app"

    (path.parent / "exists.pem").touch()

    args = ["--app", app_path, "run"]

    if ssl_certfile is not None:
        args.extend(["--ssl-certfile", str(ssl_certfile)])

    if ssl_keyfile is not None:
        args.extend(["--ssl-keyfile", ssl_keyfile])

    args.append("--create-devcert")

    result = runner.invoke(cli_command, args)

    assert result.exit_code == 1

    assert isinstance(result.exception, SystemExit)
    exc = get_click_exception(result.exception)
    assert (
        "Both certificate and key file must exists or both must not exists when using --create-devcert" in exc.message
    )


def test_no_files_provided_when_creating(
    app_file: Path, runner: CliRunner, get_click_exception: GetClickExceptionFixture
) -> None:
    path = app_file
    app_path = f"{path.stem}:app"

    args = ["--app", app_path, "run", "--create-devcert"]

    result = runner.invoke(cli_command, args)

    assert isinstance(result.exception, SystemExit)
    exc = get_click_exception(result.exception)
    assert "Both certificate and key file paths must be provided when using --create-devcert" in exc.message


@pytest.mark.parametrize(
    "ssl_certfile, ssl_keyfile",
    [("dir_exists/file.pem", "dir_not_exists/file.pem"), ("dir_not_exists/file.pem", "dir_exists/file.pem")],
)
def test_file_parent_doesnt_exists(
    app_file: Path,
    runner: CliRunner,
    ssl_certfile: Optional[str],
    ssl_keyfile: Optional[str],
    get_click_exception: GetClickExceptionFixture,
) -> None:
    path = app_file
    app_path = f"{path.stem}:app"

    (path.parent / "dir_exists").mkdir(exist_ok=True)

    args = [
        "--app",
        app_path,
        "run",
        "--ssl-certfile",
        str(ssl_certfile),
        "--ssl-keyfile",
        ssl_keyfile,
        "--create-devcert",
    ]

    result = runner.invoke(cli_command, args)

    assert result.exit_code == 1

    assert isinstance(result.exception, SystemExit)
    exc = get_click_exception(result.exception)
    assert "Directory doesn't exist" in exc.message


def test_without_cryptography_installed(
    app_file: Path,
    runner: CliRunner,
    get_click_exception: GetClickExceptionFixture,
    mocker: MockerFixture,
) -> None:
    mocker.patch("litestar.cli._utils.CRYPTOGRAPHY_INSTALLED", False)

    path = app_file
    app_path = f"{path.stem}:app"

    args = [
        "--app",
        app_path,
        "run",
        "--ssl-certfile",
        "certfile.pem",
        "--ssl-keyfile",
        "keyfile.pem",
        "--create-devcert",
    ]

    result = runner.invoke(cli_command, args)

    assert result.exit_code == 1

    assert isinstance(result.exception, SystemExit)
    exc = get_click_exception(result.exception)
    assert "Cryptogpraphy must be installed when using --create-devcert" in exc.message


@pytest.mark.usefixtures("mock_uvicorn_run")
def test_create_certificates(app_file: Path, runner: CliRunner) -> None:
    path = app_file
    app_path = f"{path.stem}:app"

    certfile_path = path.parent / "certificate.pem"
    keyfile_path = path.parent / "key.pem"

    args = [
        "--app",
        app_path,
        "run",
        "--ssl-certfile",
        str(certfile_path),
        "--ssl-keyfile",
        str(keyfile_path),
        "--create-devcert",
    ]

    result = runner.invoke(cli_command, args)

    assert result.exit_code == 0
    assert result.exception is None

    assert certfile_path.exists()
    assert keyfile_path.exists()
