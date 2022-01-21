from functools import partial

import pytest
from pydantic.fields import Undefined

from starlite import Provide


def test_fn():
    return dict()


@pytest.mark.asyncio
async def test_provide_default():
    provider = Provide(dependency=test_fn)
    value = await provider()
    assert isinstance(value, dict)


@pytest.mark.asyncio
async def test_provide_cached():
    provider = Provide(dependency=test_fn, use_cache=True)
    assert provider.value is Undefined
    value = await provider()
    assert isinstance(value, dict)
    assert provider.value == value
    second_value = await provider()
    assert value == second_value
    third_value = await provider()
    assert value == third_value


def test_provide_method():
    class MyClass:
        def my_method(self):
            assert self is MyClass

    provider = Provide(dependency=MyClass().my_method)
    assert isinstance(provider.dependency, partial)
    assert isinstance(provider.dependency.args[0], MyClass)


def test_provider_equality_check():
    def fn():
        pass

    first_provider = Provide(dependency=fn)
    second_provider = Provide(dependency=fn)

    assert first_provider == second_provider

    third_provider = Provide(dependency=fn, use_cache=True)

    assert first_provider != third_provider

    second_provider.value = True

    assert first_provider != second_provider
