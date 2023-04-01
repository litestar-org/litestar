import pytest

from litestar.testing import create_test_client


class _LifeSpanCallable:
    def __init__(self, should_raise: bool = False) -> None:
        self.called = False
        self.should_raise = should_raise

    def __call__(self) -> None:
        self.called = True
        if self.should_raise:
            raise RuntimeError("damn")


def test_life_span_startup() -> None:
    life_span_callable = _LifeSpanCallable()
    with create_test_client([], on_startup=[life_span_callable]):
        assert life_span_callable.called


def test_life_span_startup_error_handling() -> None:
    life_span_callable = _LifeSpanCallable(should_raise=True)
    with pytest.raises(RuntimeError), create_test_client([], on_startup=[life_span_callable]):
        pass


def test_life_span_shutdown() -> None:
    life_span_callable = _LifeSpanCallable()
    with create_test_client([], on_shutdown=[life_span_callable]):
        pass
    assert life_span_callable.called


def test_life_span_shutdown_error_handling() -> None:
    life_span_callable = _LifeSpanCallable(should_raise=True)
    with pytest.raises(RuntimeError), create_test_client([], on_shutdown=[life_span_callable]):
        pass
