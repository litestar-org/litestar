from unittest.mock import MagicMock

from litestar.channels.plugin import Subscriber


def test_subscriber_backlog_backoff() -> None:
    subscriber = Subscriber(plugin=MagicMock(), max_backlog=2, backlog_strategy="backoff")

    assert subscriber.put_nowait(b"foo")
    assert subscriber.put_nowait(b"bar")
    assert not subscriber.put_nowait(b"baz")

    assert subscriber.qsize == 2
    assert [subscriber._queue.get_nowait(), subscriber._queue.get_nowait()] == [b"foo", b"bar"]


def test_subscriber_backlog_dropleft() -> None:
    subscriber = Subscriber(plugin=MagicMock(), max_backlog=2, backlog_strategy="dropleft")

    assert subscriber.put_nowait(b"foo")
    assert subscriber.put_nowait(b"bar")
    assert subscriber.put_nowait(b"baz")

    assert subscriber.qsize == 2
    assert [subscriber._queue.get_nowait(), subscriber._queue.get_nowait()] == [b"bar", b"baz"]
