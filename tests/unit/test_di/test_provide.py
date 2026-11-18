import pytest

from litestar.di import Provide


def test_provide_warns_deprecation() -> None:
    async def provide_value() -> int:
        return 1

    with pytest.warns(DeprecationWarning, match="Provide") as record:
        Provide(provide_value)

    assert "Use 'litestar.di.Provider' instead" in str(record[0].message)
    assert record[0].filename == __file__


def test_provide_stores_arguments() -> None:
    def provide_value() -> int:
        return 1

    provide = Provide(provide_value, use_cache=True, sync_to_thread=True)

    assert provide.dependency is provide_value
    assert provide.use_cache is True
    assert provide.sync_to_thread is True
