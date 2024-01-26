import pytest

from litestar.config.compression import CompressionConfig
from litestar.utils.module_loader import import_string, module_to_os_path


def test_import_string() -> None:
    cls = import_string("litestar.config.compression.CompressionConfig")
    assert type(cls) == type(CompressionConfig)

    with pytest.raises(ImportError):
        _ = import_string("CompressionConfigNew")
        _ = import_string("litestar.config.compression.CompressionConfigNew")
        _ = import_string("imaginary_module_that_doesnt_exist.Config")  # a random nonexistent class


def test_module_path() -> None:
    the_path = module_to_os_path("litestar.config.compression")
    assert the_path.exists()

    with pytest.raises(TypeError):
        _ = module_to_os_path("litestar.config.compression.Config")
        _ = module_to_os_path("litestar.config.compression.extra.module")
