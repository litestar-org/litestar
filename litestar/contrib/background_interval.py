"""Generic background repeating-task plugin for Litestar.

``BackgroundIntervalPlugin`` implements :class:`litestar.plugins.InitPluginProtocol`
so it wires its own lifecycle hooks through ``on_app_init``.  The host
application is not responsible for managing background tasks directly.

NOTE: Each application instance independently loads and executes the plugin.
      If you run in clustered environments, you must ensure concurrent runs
      of this plugin do not have negative consequences.

Design rationale
~~~~~~~~~~~~~~~~
* Uses Litestar's ``lifespan`` context-manager hook so startup and shutdown
  are managed in a single, self-contained block.
* The first task run is deferred until *after* the first sleep so the plugin
  never blocks application startup.
* All exceptions inside the task function are caught and logged; they do
  **not** crash the loop.  The plugin retries on the next interval.
* A configurable jitter is added to each sleep cycle to prevent
  thundering-herd behaviour when multiple instances share a schedule.
* :class:`asyncio.CancelledError` is never swallowed -- it propagates
  immediately so graceful shutdown is always respected.

Relationship to ``BackgroundTask``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:class:`litestar.background_tasks.BackgroundTask` is designed for
**one-shot tasks triggered after an HTTP response**;
it is tied to the request/response cycle.
A periodic job must run independently of requests, so we use an
:func:`asyncio.create_task` managed through the application
lifespan instead.

Multiple periodic tasks
~~~~~~~~~~~~~~~~~~~~~~~
Register one plugin instance per task and append them all to
``AppConfig.plugins``.
The plugins compose through ``on_app_init`` without interfering with each other.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import random
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from litestar.plugins import InitPluginProtocol

__all__ = ["BackgroundIntervalPlugin"]

logger = logging.getLogger(__name__)

_MIN_INTERVAL_SECONDS: int = 60

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Awaitable, Callable

    from litestar import Litestar
    from litestar.config.app import AppConfig


class BackgroundIntervalPlugin(InitPluginProtocol):
    """Litestar plugin that calls an async callable on a semi-fixed interval.

    The task runs in the application's event loop so it is safe for async
    I/O (database calls, HTTP requests, etc.).  The first run is deferred
    until after the first sleep period to avoid startup latency.

    Raises:
        ValueError: If *interval_seconds* < 60 or *jitter_seconds* < 0.

    Examples:
    --------
    .. code-block:: python

        async def purge_expired_sessions() -> None:
            await db.execute("DELETE FROM sessions WHERE expires_at < now()")


        taskplugin = BackgroundIntervalPlugin(
            task_fn=purge_expired_sessions,
            interval_seconds=3600,
            jitter_seconds=3,
            name="session-purge",
        )

        app = Litestar(plugins=[taskplugin])
    """

    __slots__ = ("_interval", "_jitter", "_name", "_task_fn")

    def __init__(
        self,
        task_fn: Callable[[], Awaitable[None]],
        interval_seconds: int,
        jitter_seconds: int,
        name: str = "repeating-task",
    ) -> None:
        """Args:
        task_fn:
            Async callable (no arguments) invoked once per interval.  Wrap
            a callable that requires arguments with :func:`functools.partial`
            before passing it here.
        interval_seconds:
            Seconds between successive invocations.  Must be >= 60 to prevent
            accidental tight loops.
        jitter_seconds:
            Upper bound (in seconds) of a uniform random offset added to each
            sleep cycle.  Prevents all instances from firing at the exact same
            interval.
            Pass ``0`` to disable jitter entirely.
        name:
            Human-readable label used in log messages and as the
            :class:`asyncio.Task` name.  Should be unique across plugin
            instances registered with the same application.
        """
        if interval_seconds < _MIN_INTERVAL_SECONDS:
            msg = f"interval_seconds must be >= {_MIN_INTERVAL_SECONDS}, got {interval_seconds}"
            raise ValueError(msg)
        if jitter_seconds < 0:
            msg = f"jitter_seconds must be >= 0, got {jitter_seconds}"
            raise ValueError(msg)

        self._task_fn = task_fn
        self._interval = interval_seconds
        self._jitter = jitter_seconds
        self._name = name

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        """Register the repeating-task lifespan with the application.

        Called by Litestar during application construction.  Multiple
        plugin instances each append their own lifespan handler, so they
        compose without interfering with one another.
        """
        app_config.lifespan.append(self._lifespan)
        return app_config

    @asynccontextmanager
    async def _lifespan(self, _app: Litestar) -> AsyncGenerator[None, None]:
        """Spawn the background task and cancel it on shutdown."""
        logger.info(
            "%s: scheduling task every %d seconds (%d seconds jitter)",
            self._name,
            self._interval,
            self._jitter,
        )
        task = asyncio.create_task(self._loop(), name=self._name)
        try:
            yield
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            logger.info("%s: stopped", self._name)

    async def _loop(self) -> None:
        """Sleep then invoke the task callable, repeating indefinitely.

        Sleep comes first so application startup is never delayed.

        :class:`asyncio.CancelledError` (raised when the lifespan context
        exits) is never swallowed -- any other exception is logged and the
        loop continues.
        """
        while True:
            # Jitter does not require cryptographic randomness; S311 suppressed.
            jitter = random.uniform(0, self._jitter) if self._jitter else 0.0  # noqa: S311
            await asyncio.sleep(self._interval + jitter)

            logger.info("%s: starting run", self._name)
            try:
                await self._task_fn()
                logger.info("%s: completed successfully", self._name)
            except asyncio.CancelledError:
                raise  # propagate so the lifespan context can cancel cleanly
            except Exception:
                logger.exception("%s: run failed -- will retry at next interval", self._name)
