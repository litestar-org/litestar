from functools import partial
from typing import Any

import pytest
from pydantic.fields import Undefined

from starlite import Provide


class C:
    val = 31

    def __init__(self) -> None:
        self.val = 13

    @classmethod
    async def async_class(cls) -> int:
        return cls.val

    @classmethod
    def sync_class(cls) -> int:
        return cls.val

    @staticmethod
    async def async_static() -> str:
        return "one-three"

    @staticmethod
    def sync_static() -> str:
        return "one-three"

    async def async_instance(self) -> int:
        return self.val

    def sync_instance(self) -> int:
        return self.val


async def async_fn(val: str = "three-one") -> str:
    return val


def sync_fn(val: str = "three-one") -> str:
    return val


async_partial = partial(async_fn, "why-three-and-one")
sync_partial = partial(sync_fn, "why-three-and-one")


@pytest.mark.asyncio
async def test_provide_default() -> None:
    provider = Provide(dependency=async_fn)
    value = await provider()
    assert value == "three-one"


@pytest.mark.asyncio
async def test_provide_cached() -> None:
    provider = Provide(dependency=async_fn, use_cache=True)
    assert provider.value is Undefined
    value = await provider()
    assert value == "three-one"
    assert provider.value == value
    second_value = await provider()
    assert value == second_value
    third_value = await provider()
    assert value == third_value


@pytest.mark.asyncio
async def test_run_in_thread() -> None:
    provider = Provide(dependency=sync_fn, sync_to_thread=True)
    value = await provider()
    assert value == "three-one"


def test_provider_equality_check() -> None:
    first_provider = Provide(dependency=sync_fn)
    second_provider = Provide(dependency=sync_fn)
    assert first_provider == second_provider
    third_provider = Provide(dependency=sync_fn, use_cache=True)
    assert first_provider != third_provider
    second_provider.value = True
    assert first_provider != second_provider


@pytest.mark.parametrize(
    "fn, exp",
    [
        (C.async_class, 31),
        (C.sync_class, 31),
        (C.async_static, "one-three"),
        (C.sync_static, "one-three"),
        (C().async_instance, 13),
        (C().sync_instance, 13),
        (async_fn, "three-one"),
        (sync_fn, "three-one"),
        (async_partial, "why-three-and-one"),
        (sync_partial, "why-three-and-one"),
    ],
)
@pytest.mark.asyncio
async def test_provide_for_callable(fn: Any, exp: Any) -> None:
    assert await Provide(fn)() == exp
