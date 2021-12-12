from starlite import Provide


def test_fn():
    return dict()


def test_provide_default():
    provider = Provide(dependency=test_fn)
    assert isinstance(provider(), dict)


def test_provide_cached():
    provider = Provide(dependency=test_fn, use_cache=True)
    value = provider()
    assert isinstance(value, dict)
    second_value = provider()
    assert value == second_value
