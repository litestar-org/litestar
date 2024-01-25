import pytest

from litestar.config.compression import CompressionConfig
from litestar.utils.module_loader import import_string, module_to_os_path


def test_import_string() -> None:
    cls = import_string("litestar.config.compression.CompressionConfig")
    assert type(cls) == type(CompressionConfig)


def test_import_string_missing() -> None:
    try:
        cls = import_string("imaginary_module_that_doesnt_exist.Config")  # a random nonexistent class
    except ImportError:
        cls = None
    assert cls is None


def test_module_path() -> None:
    the_path = module_to_os_path("litestar.config.compression")
    assert the_path.exists()

    with pytest.raises(TypeError):
        the_path = module_to_os_path("litestar.config.compression.Config")
        the_path = module_to_os_path("litestar.config.compression.extra.module")
