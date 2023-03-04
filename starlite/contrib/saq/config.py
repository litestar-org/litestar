from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Awaitable, Optional

from starlite.exceptions.base_exceptions import MissingDependencyException

try:
    import saq  # pyright: ignore
except ImportError as e:
    raise MissingDependencyException("SAQ dependencies are not installed") from e

if TYPE_CHECKING:
    from collections.abc import Callable, Collection


@dataclass
class SaqConfig:
    """Configuration for SAQ (Simple Asynchronous Queue) for background processing."""

    functions: Collection[Callable[..., Any] | tuple[str, Callable]]
    """Functions to be called via the async workers."""
    cron_jobs: Optional[Collection[saq.CronJob]] = None
    """Cron configuration to schedule at startup."""
    startup: Optional[Callable[[dict[str, Any]], Awaitable[Any]]] = None
    """Async function called on worker startup."""
    shutdown: Optional[Callable[[dict[str, Any]], Awaitable[Any]]] = None
    """Async function called on worker shutdown."""
    before_process: Optional[Callable[[dict[str, Any]], Awaitable[Any]]] = None
    """Async function called before a job processes."""
    after_process: Optional[Callable[[dict[str, Any]], Awaitable[Any]]] = None
    """Async function called after a job processes."""
    workers: int = field(default=1)
    """The number of workers processes to start."""
    concurrency: int = field(default=10)
    """The number of jobs allowed to execute simultaneously per worker."""
