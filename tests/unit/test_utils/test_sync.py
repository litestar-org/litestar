from collections.abc import Iterator

import pytest

from litestar.utils.sync import AsyncIteratorWrapper, IteratorExhaustedError, ensure_async_callable


async def test_function_wrapper_wraps_method_correctly() -> None:
    class MyClass:
        def __init__(self) -> None:
            self.value = 0

        def my_method(self, value: int) -> None:
            self.value = value

    instance = MyClass()

    wrapped_method = ensure_async_callable(instance.my_method)

    await wrapped_method(1)
    assert instance.value == 1

    await wrapped_method(value=10)
    assert instance.value == 10


async def test_function_wrapper_wraps_async_method_correctly() -> None:
    class MyClass:
        def __init__(self) -> None:
            self.value = 0

        async def my_method(self, value: int) -> None:
            self.value = value

    instance = MyClass()

    wrapped_method = ensure_async_callable(instance.my_method)

    await wrapped_method(1)
    assert instance.value == 1

    await wrapped_method(value=10)
    assert instance.value == 10


async def test_function_wrapper_wraps_function_correctly() -> None:
    obj = {"value": 0}

    def my_function(new_value: int) -> None:
        obj["value"] = new_value

    wrapped_function = ensure_async_callable(my_function)

    await wrapped_function(1)
    assert obj["value"] == 1

    await wrapped_function(new_value=10)
    assert obj["value"] == 10


async def test_function_wrapper_wraps_async_function_correctly() -> None:
    obj = {"value": 0}

    async def my_function(new_value: int) -> None:
        obj["value"] = new_value

    wrapped_function = ensure_async_callable(my_function)

    await wrapped_function(1)
    assert obj["value"] == 1

    await wrapped_function(new_value=10)
    assert obj["value"] == 10


async def test_function_wrapper_wraps_class_correctly() -> None:
    class MyCallable:
        value = 0

        def __call__(self, new_value: int) -> None:
            self.value = new_value

    instance = MyCallable()

    wrapped_class = ensure_async_callable(instance)

    await wrapped_class(1)
    assert instance.value == 1

    await wrapped_class(new_value=10)
    assert instance.value == 10


async def test_function_wrapper_wraps_async_class_correctly() -> None:
    class MyCallable:
        value = 0

        async def __call__(self, new_value: int) -> None:
            self.value = new_value

    instance = MyCallable()

    wrapped_class = ensure_async_callable(instance)

    await wrapped_class(1)
    assert instance.value == 1

    await wrapped_class(new_value=10)
    assert instance.value == 10


async def test_async_iterator_wrapper_yields_all_values() -> None:
    assert [v async for v in AsyncIteratorWrapper([1, 2, 3])] == [1, 2, 3]


async def test_async_iterator_wrapper_propagates_value_error_from_wrapped_iterator() -> None:
    # a ``ValueError`` raised by the wrapped iterator must not be mistaken for exhaustion
    def gen() -> Iterator[int]:
        yield 1
        yield 2
        raise ValueError("boom")

    received = []
    with pytest.raises(ValueError, match="boom"):
        async for value in AsyncIteratorWrapper(gen()):
            received.append(value)

    assert received == [1, 2]


@pytest.mark.parametrize("values", [[], [None], [0, "", False, None, b"", []]])
async def test_async_iterator_wrapper_does_not_mistake_values_for_exhaustion(values: list) -> None:
    assert [v async for v in AsyncIteratorWrapper(values)] == values


@pytest.mark.parametrize("exc_type", [RuntimeError, KeyError])
async def test_async_iterator_wrapper_propagates_exceptions_from_wrapped_iterator(
    exc_type: type[BaseException],
) -> None:
    def gen() -> Iterator[int]:
        yield 1
        raise exc_type()

    received = []
    with pytest.raises(exc_type):
        async for value in AsyncIteratorWrapper(gen()):
            received.append(value)

    assert received == [1]


def test_async_iterator_wrapper_call_next_raises_iterator_exhausted_error() -> None:
    wrapper = AsyncIteratorWrapper([1])

    assert wrapper._call_next() == 1
    with pytest.raises(IteratorExhaustedError):
        wrapper._call_next()
