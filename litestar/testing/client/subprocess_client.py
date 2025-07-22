import pathlib
import socket
import subprocess
import time
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncIterator, Iterator

import httpx


class StartupError(RuntimeError):
    pass


def _get_available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        # Bind to a free port provided by the host
        try:
            sock.bind(("localhost", 0))
        except OSError as e:  # pragma: no cover
            raise StartupError("Could not find an open port") from e
        else:
            port: int = sock.getsockname()[1]
            return port


@contextmanager
def run_app(workdir: pathlib.Path, app: str, retry_count: int = 100, retry_timeout: int = 1) -> Iterator[str]:
    """Launch a litestar application in a subprocess with a random available port.

    Args:
        workdir: Path to working directory where run command will be executed
        app: Path to Litestar application, e.g.: "my_app:application"
        retry_count: Number of retries to wait for the application to start
        retry_timeout: Timeout in seconds to wait between retries

    Raises:
        StartupError: If the application fails to start with given retry count and timeout
    """
    port = _get_available_port()
    with subprocess.Popen(
        args=["litestar", "--app", app, "run", "--port", str(port)],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        cwd=workdir,
    ) as proc:
        url = f"http://127.0.0.1:{port}"
        application_started = False

        for _ in range(retry_count):
            try:
                httpx.get(url, timeout=0.1)
                application_started = True
                break
            except httpx.TransportError:
                time.sleep(retry_timeout)

        if not application_started:
            proc.kill()
            raise StartupError("Application failed to start")

        yield url
        proc.kill()


@asynccontextmanager
async def subprocess_async_client(workdir: pathlib.Path, app: str) -> AsyncIterator[httpx.AsyncClient]:
    """Provides an async httpx client for a litestar app launched in a subprocess.

    Args:
        workdir: Path to the directory in which the app module resides.
        app: Uvicorn app string that can be resolved in the provided working directory, e.g.: "app:app"
    """
    with run_app(workdir=workdir, app=app) as url:
        async with httpx.AsyncClient(base_url=url) as client:
            yield client


@contextmanager
def subprocess_sync_client(workdir: pathlib.Path, app: str) -> Iterator[httpx.Client]:
    """Provides a sync httpx client for a litestar app launched in a subprocess.

    Args:
        workdir: Path to the directory in which the app module resides.
        app: Uvicorn app string that can be resolved in the provided working directory, e.g.: "app:app"
    """
    with run_app(workdir=workdir, app=app) as url, httpx.Client(base_url=url) as client:
        yield client
