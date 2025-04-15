import pytest  # pyright: ignore


@pytest.mark.flaky(reruns=3)
def test_re_exports() -> None:
    from advanced_alchemy import base as sa_base  # pyright: ignore
    from advanced_alchemy import mixins as sa_mixins  # pyright: ignore
    from advanced_alchemy import operations as sa_operations  # pyright: ignore
    from advanced_alchemy.extensions import litestar as sa_litestar  # pyright: ignore
    from advanced_alchemy.extensions.litestar import exceptions as sa_exceptions  # pyright: ignore
    from advanced_alchemy.extensions.litestar import filters as sa_filters  # pyright: ignore
    from advanced_alchemy.extensions.litestar import repository as sa_repository  # pyright: ignore
    from advanced_alchemy.extensions.litestar import service as sa_service  # pyright: ignore
    from advanced_alchemy.extensions.litestar import types as sa_types  # pyright: ignore
    from advanced_alchemy.extensions.litestar import utils as sa_utils  # pyright: ignore

    from litestar.plugins import sqlalchemy  # pyright: ignore

    # Test module imports
    assert sqlalchemy.base is sa_base
    assert sqlalchemy.exceptions is sa_exceptions
    assert sqlalchemy.filters is sa_filters
    assert sqlalchemy.mixins is sa_mixins
    assert sqlalchemy.operations is sa_operations
    assert sqlalchemy.repository is sa_repository
    assert sqlalchemy.service is sa_service
    assert sqlalchemy.types is sa_types
    assert sqlalchemy.utils is sa_utils

    # Test symbol imports from advanced_alchemy.extensions.litestar
    assert sqlalchemy.AlembicAsyncConfig is sa_litestar.AlembicAsyncConfig
    assert sqlalchemy.AlembicCommands is sa_litestar.AlembicCommands
    assert sqlalchemy.AlembicSyncConfig is sa_litestar.AlembicSyncConfig
    assert sqlalchemy.AsyncSessionConfig is sa_litestar.AsyncSessionConfig
    assert sqlalchemy.EngineConfig is sa_litestar.EngineConfig
    assert sqlalchemy.SQLAlchemyAsyncConfig is sa_litestar.SQLAlchemyAsyncConfig
    assert sqlalchemy.SQLAlchemyDTO is sa_litestar.SQLAlchemyDTO
    assert sqlalchemy.SQLAlchemyDTOConfig is sa_litestar.SQLAlchemyDTOConfig
    assert sqlalchemy.SQLAlchemyInitPlugin is sa_litestar.SQLAlchemyInitPlugin
    assert sqlalchemy.SQLAlchemyPlugin is sa_litestar.SQLAlchemyPlugin
    assert sqlalchemy.SQLAlchemySerializationPlugin is sa_litestar.SQLAlchemySerializationPlugin
    assert sqlalchemy.SQLAlchemySyncConfig is sa_litestar.SQLAlchemySyncConfig
    assert sqlalchemy.SyncSessionConfig is sa_litestar.SyncSessionConfig

    # Test additional symbol imports from advanced_alchemy.extensions.litestar
    assert sqlalchemy.async_autocommit_before_send_handler is sa_litestar.async_autocommit_before_send_handler
    assert sqlalchemy.async_autocommit_handler_maker is sa_litestar.async_autocommit_handler_maker
    assert sqlalchemy.async_default_before_send_handler is sa_litestar.async_default_before_send_handler
    assert sqlalchemy.async_default_handler_maker is sa_litestar.async_default_handler_maker
    assert sqlalchemy.get_database_migration_plugin is sa_litestar.get_database_migration_plugin
    assert sqlalchemy.providers is sa_litestar.providers
    assert sqlalchemy.sync_autocommit_before_send_handler is sa_litestar.sync_autocommit_before_send_handler
    assert sqlalchemy.sync_autocommit_handler_maker is sa_litestar.sync_autocommit_handler_maker
    assert sqlalchemy.sync_default_before_send_handler is sa_litestar.sync_default_before_send_handler
    assert sqlalchemy.sync_default_handler_maker is sa_litestar.sync_default_handler_maker


def test_getattr() -> None:
    """Test the __getattr__ function for non-existent attributes."""
    from litestar.plugins import sqlalchemy  # pyright: ignore

    # Test that accessing a non-existent attribute raises an AttributeError
    with pytest.raises(AttributeError) as excinfo:  # pyright: ignore
        _ = sqlalchemy.non_existent_attribute

    assert "has no attribute 'non_existent_attribute'" in str(excinfo.value)


def test_base_exports() -> None:
    """Test the base module exports."""
    from advanced_alchemy import base as sa_base  # pyright: ignore

    from litestar.plugins.sqlalchemy import base  # pyright: ignore

    # Test all exported symbols
    for symbol in base.__all__:  # pyright: ignore
        assert getattr(base, symbol) is getattr(sa_base, symbol)

    # Test error case
    with pytest.raises(AttributeError) as excinfo:  # pyright: ignore
        _ = base.non_existent_attribute  # type: ignore[attr-defined]

    assert "has no attribute 'non_existent_attribute'" in str(excinfo.value)


def test_exceptions_exports() -> None:
    """Test the exceptions module exports."""
    from advanced_alchemy import exceptions as sa_exceptions  # pyright: ignore

    from litestar.plugins.sqlalchemy import exceptions  # pyright: ignore

    # Test all exported symbols
    for symbol in exceptions.__all__:  # pyright: ignore
        assert getattr(exceptions, symbol) is getattr(sa_exceptions, symbol)

    # Test error case
    with pytest.raises(AttributeError) as excinfo:  # pyright: ignore
        _ = exceptions.non_existent_attribute  # type: ignore[attr-defined]

    assert "has no attribute 'non_existent_attribute'" in str(excinfo.value)


def test_filters_exports() -> None:
    """Test the filters module exports."""
    from advanced_alchemy import filters as sa_filters  # pyright: ignore

    from litestar.plugins.sqlalchemy import filters  # pyright: ignore

    # Test all exported symbols
    for symbol in filters.__all__:  # pyright: ignore
        assert getattr(filters, symbol) is getattr(sa_filters, symbol)

    # Test error case
    with pytest.raises(AttributeError) as excinfo:  # pyright: ignore
        _ = filters.non_existent_attribute  # type: ignore[attr-defined]

    assert "has no attribute 'non_existent_attribute'" in str(excinfo.value)


def test_mixins_exports() -> None:
    """Test the mixins module exports."""
    from advanced_alchemy import mixins as sa_mixins  # pyright: ignore

    from litestar.plugins.sqlalchemy import mixins  # pyright: ignore

    # Test all exported symbols
    for symbol in mixins.__all__:  # pyright: ignore
        assert getattr(mixins, symbol) is getattr(sa_mixins, symbol)

    # Test error case
    with pytest.raises(AttributeError) as excinfo:  # pyright: ignore
        _ = mixins.non_existent_attribute  # type: ignore[attr-defined]

    assert "has no attribute 'non_existent_attribute'" in str(excinfo.value)


def test_operations_exports() -> None:
    """Test the operations module exports."""

    from litestar.plugins.sqlalchemy import operations  # pyright: ignore

    # Test error case
    with pytest.raises(AttributeError) as excinfo:  # pyright: ignore
        _ = operations.non_existent_attribute  # type: ignore[attr-defined]

    assert "has no attribute 'non_existent_attribute'" in str(excinfo.value)


def test_repository_exports() -> None:
    """Test the repository module exports."""
    from advanced_alchemy import repository as sa_repository  # pyright: ignore

    from litestar.plugins.sqlalchemy import repository  # pyright: ignore

    # Test all exported symbols
    for symbol in repository.__all__:  # pyright: ignore
        assert getattr(repository, symbol) is getattr(sa_repository, symbol)

    # Test error case
    with pytest.raises(AttributeError) as excinfo:  # pyright: ignore
        _ = repository.non_existent_attribute  # type: ignore[attr-defined]

    assert "has no attribute 'non_existent_attribute'" in str(excinfo.value)


def test_service_exports() -> None:
    """Test the service module exports."""
    from advanced_alchemy import service as sa_service  # pyright: ignore

    from litestar.plugins.sqlalchemy import service  # pyright: ignore

    # Test all exported symbols
    for symbol in service.__all__:  # pyright: ignore
        assert getattr(service, symbol) is getattr(sa_service, symbol)

    # Test error case
    with pytest.raises(AttributeError) as excinfo:  # pyright: ignore
        _ = service.non_existent_attribute  # type: ignore[attr-defined]

    assert "has no attribute 'non_existent_attribute'" in str(excinfo.value)


def test_types_exports() -> None:
    """Test the types module exports."""
    from advanced_alchemy import types as sa_types  # pyright: ignore

    from litestar.plugins.sqlalchemy import types  # pyright: ignore

    # Test all exported symbols
    for symbol in types.__all__:  # pyright: ignore
        assert getattr(types, symbol) is getattr(sa_types, symbol)

    # Test error case
    with pytest.raises(AttributeError) as excinfo:  # pyright: ignore
        _ = types.non_existent_attribute  # type: ignore[attr-defined]

    assert "has no attribute 'non_existent_attribute'" in str(excinfo.value)


def test_utils_exports() -> None:
    """Test the utils module exports."""
    import importlib

    from litestar.plugins.sqlalchemy import utils  # pyright: ignore

    # Test each exported symbol
    for symbol in [
        "text",
        "singleton",
        "module_loader",
        "dataclass",
        "sync_tools",
        "portals",
        "deprecation",
    ]:
        # Import the submodule directly from advanced_alchemy.utils
        sa_module = importlib.import_module(f"advanced_alchemy.utils.{symbol}")
        assert getattr(utils, symbol) is sa_module

    # Test error case
    with pytest.raises(AttributeError) as excinfo:  # pyright: ignore
        _ = utils.non_existent_attribute  # type: ignore[attr-defined]

    # The error message should come from advanced_alchemy.utils since that's what we're re-exporting
    assert "has no attribute 'non_existent_attribute'" in str(excinfo.value)
