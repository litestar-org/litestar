"""Unit tests for BackgroundIntervalPlugin.

Async tests use ``pytest-anyio`` (``@pytest.mark.anyio``) consistent with
the rest of litestar's test suite.  ``asyncio.sleep`` is always patched to
a controlled coroutine so tests run in microseconds without a strong
wall-clock dependency.

Run with::

    pytest tests/contrib/test_background_interval.py -v
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from litestar.contrib.background_interval import _MIN_INTERVAL_SECONDS, BackgroundIntervalPlugin

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_plugin(
    task_fn: AsyncMock | None = None,
    interval_seconds: int = 60,
    jitter_seconds: int = 0,
    name: str = "test-task",
) -> BackgroundIntervalPlugin:
    """Return a plugin wired with a no-op async callable by default."""
    return BackgroundIntervalPlugin(
        task_fn=task_fn if task_fn is not None else AsyncMock(),
        interval_seconds=interval_seconds,
        jitter_seconds=jitter_seconds,
        name=name,
    )


async def _run_loop_n_cycles(plugin: BackgroundIntervalPlugin, *, n: int) -> None:
    """Drive ``_loop`` through *n* complete sleep/run cycles then stop it.

    Patches ``asyncio.sleep`` to a no-op.  After *n* calls the mock raises
    :class:`asyncio.CancelledError`, mirroring what the lifespan context does
    on application shutdown.
    """
    sleep_count = 0

    async def controlled_sleep(_seconds: float) -> None:
        nonlocal sleep_count
        sleep_count += 1
        if sleep_count > n:
            raise asyncio.CancelledError

    with patch("litestar.contrib.background_interval.asyncio.sleep", side_effect=controlled_sleep):
        with pytest.raises(asyncio.CancelledError):
            await plugin._loop()


# ---------------------------------------------------------------------------
# Construction / validation
# ---------------------------------------------------------------------------


def test_background_interval_plugin_accepts_valid_arguments() -> None:
    plugin = _make_plugin(interval_seconds=120, jitter_seconds=30)
    assert plugin._interval == 120
    assert plugin._jitter == 30


def test_background_interval_plugin_accepts_minimum_interval() -> None:
    _make_plugin(interval_seconds=_MIN_INTERVAL_SECONDS)


def test_background_interval_plugin_rejects_interval_below_minimum() -> None:
    with pytest.raises(ValueError, match="interval_seconds must be"):
        _make_plugin(interval_seconds=_MIN_INTERVAL_SECONDS - 1)


def test_background_interval_plugin_rejects_zero_interval() -> None:
    with pytest.raises(ValueError):
        _make_plugin(interval_seconds=0)


def test_background_interval_plugin_accepts_zero_jitter() -> None:
    plugin = _make_plugin(jitter_seconds=0)
    assert plugin._jitter == 0


def test_background_interval_plugin_rejects_negative_jitter() -> None:
    with pytest.raises(ValueError, match="jitter_seconds must be"):
        _make_plugin(jitter_seconds=-1)


def test_background_interval_plugin_stores_name() -> None:
    plugin = _make_plugin(name="my-task")
    assert plugin._name == "my-task"


# ---------------------------------------------------------------------------
# on_app_init
# ---------------------------------------------------------------------------


def test_on_app_init_appends_lifespan_handler() -> None:
    plugin = _make_plugin()
    app_config = MagicMock()
    app_config.lifespan = []

    result = plugin.on_app_init(app_config)

    assert plugin._lifespan in app_config.lifespan
    assert result is app_config


def test_on_app_init_multiple_plugins_each_append_once() -> None:
    plugin_a = _make_plugin(name="task-a")
    plugin_b = _make_plugin(name="task-b")
    app_config = MagicMock()
    app_config.lifespan = []

    plugin_a.on_app_init(app_config)
    plugin_b.on_app_init(app_config)

    assert len(app_config.lifespan) == 2
    assert plugin_a._lifespan in app_config.lifespan
    assert plugin_b._lifespan in app_config.lifespan


# ---------------------------------------------------------------------------
# _loop: execution behaviour
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_loop_calls_task_fn_after_each_sleep() -> None:
    task_fn = AsyncMock()
    plugin = _make_plugin(task_fn=task_fn)

    await _run_loop_n_cycles(plugin, n=3)

    assert task_fn.call_count == 3


@pytest.mark.anyio
async def test_loop_sleeps_before_first_task_run() -> None:
    """Task must never run before the first sleep completes."""
    events: list[str] = []
    sleep_count = 0

    async def task_fn() -> None:
        events.append("task")

    async def controlled_sleep(_seconds: float) -> None:
        nonlocal sleep_count
        events.append("sleep")
        sleep_count += 1
        if sleep_count > 1:
            raise asyncio.CancelledError

    plugin = _make_plugin(task_fn=task_fn)
    with patch("litestar.contrib.background_interval.asyncio.sleep", side_effect=controlled_sleep):
        with pytest.raises(asyncio.CancelledError):
            await plugin._loop()

    assert events[0] == "sleep"
    assert events[1] == "task"


@pytest.mark.anyio
async def test_loop_continues_after_task_exception() -> None:
    call_count = 0

    async def flaky_task() -> None:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("transient error")

    plugin = _make_plugin(task_fn=flaky_task)

    await _run_loop_n_cycles(plugin, n=2)

    assert call_count == 2


@pytest.mark.anyio
async def test_loop_logs_task_exception(caplog: pytest.LogCaptureFixture) -> None:
    async def broken_task() -> None:
        raise ValueError("boom")

    plugin = _make_plugin(task_fn=broken_task, name="boom-task")

    with caplog.at_level(logging.ERROR):
        await _run_loop_n_cycles(plugin, n=1)

    assert any("boom-task" in r.message and "retry" in r.message for r in caplog.records)


@pytest.mark.anyio
async def test_loop_propagates_cancelled_error_from_sleep() -> None:
    task_fn = AsyncMock()
    plugin = _make_plugin(task_fn=task_fn)

    async def cancel_immediately(_seconds: float) -> None:
        raise asyncio.CancelledError

    with patch("litestar.contrib.background_interval.asyncio.sleep", side_effect=cancel_immediately):
        with pytest.raises(asyncio.CancelledError):
            await plugin._loop()

    task_fn.assert_not_called()


@pytest.mark.anyio
async def test_loop_propagates_cancelled_error_from_task() -> None:
    async def cancellable_task() -> None:
        raise asyncio.CancelledError

    plugin = _make_plugin(task_fn=cancellable_task)

    async def noop_sleep(_seconds: float) -> None:
        return

    with patch("litestar.contrib.background_interval.asyncio.sleep", side_effect=noop_sleep):
        with pytest.raises(asyncio.CancelledError):
            await plugin._loop()


# ---------------------------------------------------------------------------
# _loop: sleep duration
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_loop_sleeps_exact_interval_when_jitter_is_zero() -> None:
    sleep_durations: list[float] = []

    async def recording_sleep(seconds: float) -> None:
        sleep_durations.append(seconds)
        if len(sleep_durations) >= 2:
            raise asyncio.CancelledError

    plugin = _make_plugin(interval_seconds=300, jitter_seconds=0)
    with patch("litestar.contrib.background_interval.asyncio.sleep", side_effect=recording_sleep):
        with pytest.raises(asyncio.CancelledError):
            await plugin._loop()

    assert all(d == 300.0 for d in sleep_durations)


@pytest.mark.anyio
async def test_loop_sleep_duration_bounded_by_interval_plus_jitter() -> None:
    sleep_durations: list[float] = []

    async def recording_sleep(seconds: float) -> None:
        sleep_durations.append(seconds)
        if len(sleep_durations) >= 5:
            raise asyncio.CancelledError

    plugin = _make_plugin(interval_seconds=300, jitter_seconds=60)
    with patch("litestar.contrib.background_interval.asyncio.sleep", side_effect=recording_sleep):
        with pytest.raises(asyncio.CancelledError):
            await plugin._loop()

    for d in sleep_durations:
        assert 300.0 <= d <= 360.0


@pytest.mark.anyio
async def test_loop_jitter_varies_across_cycles() -> None:
    """Jitter must produce distinct durations across cycles (with overwhelming probability)."""
    sleep_durations: list[float] = []
    n_cycles = 20

    async def recording_sleep(seconds: float) -> None:
        sleep_durations.append(seconds)
        if len(sleep_durations) >= n_cycles:
            raise asyncio.CancelledError

    plugin = _make_plugin(interval_seconds=300, jitter_seconds=1200)
    with patch("litestar.contrib.background_interval.asyncio.sleep", side_effect=recording_sleep):
        with pytest.raises(asyncio.CancelledError):
            await plugin._loop()

    assert len(set(sleep_durations)) > 1, "jitter produced identical values every cycle"


# ---------------------------------------------------------------------------
# _lifespan
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_lifespan_cancels_background_task_on_exit() -> None:
    started = asyncio.Event()

    async def long_running_task() -> None:
        started.set()
        await asyncio.sleep(10_000)

    plugin = _make_plugin(task_fn=long_running_task)
    mock_app = MagicMock()

    real_sleep = asyncio.sleep
    call_count = 0

    async def controlled_sleep(seconds: float) -> None:
        nonlocal call_count
        call_count += 1

        # First sleep: let loop advance immediately
        if call_count == 1:
            return

        # Subsequent sleeps: block "forever" using real sleep
        await real_sleep(10_000)

    with patch(
        "litestar.contrib.background_interval.asyncio.sleep",
        side_effect=controlled_sleep,
    ):
        async with plugin._lifespan(mock_app):
            await asyncio.wait_for(started.wait(), timeout=1.0)
    # Reaching here means the lifespan context exited cleanly and the
    # internal asyncio.Task was cancelled without error.


@pytest.mark.anyio
async def test_lifespan_logs_startup(caplog: pytest.LogCaptureFixture) -> None:
    plugin = _make_plugin(name="log-test", interval_seconds=60, jitter_seconds=30)
    mock_app = MagicMock()

    async def cancel_on_sleep(_seconds: float) -> None:
        raise asyncio.CancelledError

    with caplog.at_level(logging.INFO):
        with patch("litestar.contrib.background_interval.asyncio.sleep", side_effect=cancel_on_sleep):
            async with plugin._lifespan(mock_app):
                pass

    messages = [r.message for r in caplog.records]
    assert any("log-test" in m and "60" in m for m in messages)


@pytest.mark.anyio
async def test_lifespan_logs_shutdown(caplog: pytest.LogCaptureFixture) -> None:
    plugin = _make_plugin(name="shutdown-test")
    mock_app = MagicMock()

    async def cancel_on_sleep(_seconds: float) -> None:
        raise asyncio.CancelledError

    with caplog.at_level(logging.INFO):
        with patch("litestar.contrib.background_interval.asyncio.sleep", side_effect=cancel_on_sleep):
            async with plugin._lifespan(mock_app):
                pass

    messages = [r.message for r in caplog.records]
    assert any("shutdown-test" in m and "stopped" in m for m in messages)
