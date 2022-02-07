from time import sleep

from starlite.caching import SimpleCacheBackend


def test_naive_cache_backend():
    backend = SimpleCacheBackend()
    backend.set("test", "1", 0.1)  # type: ignore
    assert backend.get("test")
    sleep(0.2)
    assert not backend.get("test")
