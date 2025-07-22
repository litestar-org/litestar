"""
Test the app running in a subprocess
"""

import asyncio
import pathlib
import sys
from typing import AsyncIterator, Iterator

import httpx
import httpx_sse
import pytest

from litestar.testing import subprocess_async_client, subprocess_sync_client
from litestar.testing.client.subprocess_client import StartupError, run_app

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

ROOT = pathlib.Path(__file__).parent
APP = "demo:app"


@pytest.fixture(name="async_client")
async def fx_async_client() -> AsyncIterator[httpx.AsyncClient]:
    async with subprocess_async_client(workdir=ROOT, app=APP) as client:
        yield client


@pytest.fixture(name="sync_client")
def fx_sync_client() -> Iterator[httpx.Client]:
    with subprocess_sync_client(workdir=ROOT, app=APP) as client:
        yield client


async def test_run_app() -> None:
    """Ensure that method returns application url if started successfully"""
    with run_app(workdir=ROOT, app=APP) as url:
        assert isinstance(url, str)
        assert url.startswith("http://127.0.0.1:")


async def test_run_app_exception() -> None:
    """
    Ensure that method throws a StartupError if the application fails to start.
    To simulate this, we set retry_count=0, so that we don't check if the application has started.
    """
    with pytest.raises(StartupError):
        with run_app(workdir=ROOT, app=APP, retry_count=0):
            ...


async def test_subprocess_async_client(async_client: httpx.AsyncClient) -> None:
    """Demonstrates functionality of the async client with an infinite SSE source that cannot be tested with the
    regular async test client.
    """

    async with httpx_sse.aconnect_sse(async_client, "GET", "/notify/hello") as event_source:
        async for event in event_source.aiter_sse():
            assert event.data == "hello"
            break


def test_subprocess_sync_client(sync_client: httpx.Client) -> None:
    """Demonstrates functionality of the async client with an infinite SSE source that cannot be tested with the
    regular async test client.
    """

    with httpx_sse.connect_sse(sync_client, "GET", "/notify/hello") as event_source:
        for event in event_source.iter_sse():
            assert event.data == "hello"
            break
