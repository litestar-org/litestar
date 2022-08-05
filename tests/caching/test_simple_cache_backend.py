from time import sleep

from starlite.cache import SimpleCacheBackend


def test_simple_cache_backend() -> None:
    backend = SimpleCacheBackend()
    backend.set("test", "1", 0.1)  # type: ignore
    assert backend.get("test")
    sleep(0.2)
    assert not backend.get("test")
