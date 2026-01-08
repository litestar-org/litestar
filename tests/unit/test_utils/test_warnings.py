import warnings
from collections.abc import Generator

import pytest

from litestar.exceptions import LitestarWarning
from litestar.utils.warnings import warn_sync_to_thread_with_generator


def _create_sample_generator() -> Generator[int, None, None]:
    yield 1


def test_warn_sync_to_thread_with_generator_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LITESTAR_WARN_SYNC_TO_THREAD_WITH_GENERATOR", raising=False)

    with pytest.warns(LitestarWarning, match="sync_to_thread.*generator"):
        warn_sync_to_thread_with_generator(_create_sample_generator())


def test_warn_sync_to_thread_with_generator_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LITESTAR_WARN_SYNC_TO_THREAD_WITH_GENERATOR", "0")

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        warn_sync_to_thread_with_generator(_create_sample_generator())


def test_warn_sync_to_thread_with_generator_disabled_false_string(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LITESTAR_WARN_SYNC_TO_THREAD_WITH_GENERATOR", "false")

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        warn_sync_to_thread_with_generator(_create_sample_generator())
