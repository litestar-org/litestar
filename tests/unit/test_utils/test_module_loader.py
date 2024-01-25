from litestar.config.compression import CompressionConfig
from litestar.utils.module_loader import import_string


def test_import_string() -> None:
    cls = import_string("litestar.config.compression.CompressionConfig")
    assert type(cls) == type(CompressionConfig)


def test_import_string_missing() -> None:
    try:
        cls = import_string("imaginary_module_that_doesnt_exist.Config")  # a random nonexistent class
    except ImportError:
        cls = None
    assert cls is None
