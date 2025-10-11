from collections.abc import AsyncIterator, Generator
from typing import TypeVar, Union

from pytest import raises

from litestar.response.streaming import ClientDisconnectError
from litestar.utils.sync import AsyncIteratorWrapper

T = TypeVar("T")


class GeneratorException(Exception): ...


async def anext(iterator: AsyncIterator[T]) -> T:
    return await iterator.__anext__()


def generator(state: list[int], iterations: int) -> Generator[int, Union[int, None]]:
    try:
        for _ in range(iterations):
            received = yield state[0]
            state[0] += 1

            if received is not None:
                state.append(received)

    except ClientDisconnectError as error:
        raise GeneratorException from error

    finally:
        state.append(-1)


async def test_async_iterator_wrapper() -> None:
    state = [0]
    iterations = 10
    async_iterator = AsyncIteratorWrapper(generator(state, iterations))

    async for i in async_iterator:
        assert state[0] == i

    assert state[-1] == -1


async def test_async_iterator_wrapper_aclose() -> None:
    state = [0]
    async_iterator = AsyncIteratorWrapper(generator(state, 10))

    await anext(async_iterator)
    await async_iterator.aclose()

    assert state[-1] == -1


async def test_async_iterator_wrapper_asend() -> None:
    state = [0]
    async_iterator: AsyncIteratorWrapper[int, int] = AsyncIteratorWrapper(generator(state, 10))
    await anext(async_iterator)

    assert await async_iterator.asend(10) == 1
    assert state[-1] == 10


async def test_async_iterator_wrapper_athrow() -> None:
    state = [0]
    async_iterator = AsyncIteratorWrapper(generator(state, 10))
    await anext(async_iterator)

    with raises(GeneratorException):
        await async_iterator.athrow(ClientDisconnectError)

    assert state[-1] == -1


async def async_iterator_wrapper_from_iterable() -> None:
    iterator = iter(range(3))
    async_iterator = AsyncIteratorWrapper(iterator)

    assert [i async for i in async_iterator] == [0, 1, 2]


async def async_iterator_wrapper_from_iterable_aclose() -> None:
    iterator = iter(range(3))
    async_iterator = AsyncIteratorWrapper(iterator)

    await anext(async_iterator)
    await async_iterator.aclose()

    with raises(StopAsyncIteration):
        await anext(async_iterator)


async def async_iterator_wrapper_from_iterable_asend() -> None:
    iterator = iter(range(3))
    async_iterator: AsyncIteratorWrapper[int, int] = AsyncIteratorWrapper(iterator)
    await anext(async_iterator)

    assert await async_iterator.asend(10) == 1


async def async_iterator_wrapper_from_iterable_athrow() -> None:
    iterator = iter(range(3))
    async_iterator = AsyncIteratorWrapper(iterator)
    await anext(async_iterator)

    with raises(StopAsyncIteration):
        await async_iterator.athrow(StopIteration)
