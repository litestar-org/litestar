from starlite.middleware.compression.gzip import GZipMiddleware
from starlite.utils import import_string


def test_import_string() -> None:
    cls = import_string("starlite.middleware.compression.gzip.GZipMiddleware")
    assert type(cls) == type(GZipMiddleware)


def test_import_string_missing() -> None:
    try:
        cls = import_string("starlite.middleware.compression.gzip.BadClass")
    except ImportError:
        cls = None
    assert cls is None
