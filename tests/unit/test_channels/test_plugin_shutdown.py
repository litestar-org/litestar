from __future__ import annotations

import asyncio

from litestar.channels import ChannelsPlugin
from litestar.channels.backends.memory import MemoryChannelsBackend


async def test_shutdown_clears_task_references(memory_backend: MemoryChannelsBackend) -> None:
    plugin = ChannelsPlugin(backend=memory_backend, arbitrary_channels_allowed=True)

    await plugin._on_startup()

    pub_task = plugin._pub_task
    sub_task = plugin._sub_task
    pub_queue = plugin._pub_queue

    assert pub_task is not None
    assert sub_task is not None
    assert pub_queue is not None

    await plugin._on_shutdown()

    assert pub_task.cancelled() or pub_task.done()
    assert sub_task.cancelled() or sub_task.done()
    assert plugin._pub_task is None
    assert plugin._sub_task is None
    assert plugin._pub_queue is None


async def test_shutdown_idempotent_with_task_verification(memory_backend: MemoryChannelsBackend) -> None:
    plugin = ChannelsPlugin(backend=memory_backend, arbitrary_channels_allowed=True)

    await plugin._on_shutdown()
    pub_task_1 = plugin._pub_task
    sub_task_1 = plugin._sub_task
    assert pub_task_1 is None
    assert sub_task_1 is None

    await plugin._on_startup()
    pub_task_2 = plugin._pub_task
    sub_task_2 = plugin._sub_task
    assert pub_task_2 is not None
    assert sub_task_2 is not None

    await plugin._on_shutdown()
    await plugin._on_shutdown()
    pub_task_3 = plugin._pub_task
    sub_task_3 = plugin._sub_task
    assert pub_task_3 is None
    assert sub_task_3 is None


async def test_startup_after_shutdown_creates_new_tasks(memory_backend: MemoryChannelsBackend) -> None:
    plugin = ChannelsPlugin(backend=memory_backend, arbitrary_channels_allowed=True)

    await plugin._on_startup()
    first_pub_task = plugin._pub_task
    first_sub_task = plugin._sub_task
    assert first_pub_task is not None
    assert first_sub_task is not None

    await plugin._on_shutdown()
    pub_task_after_shutdown = plugin._pub_task
    sub_task_after_shutdown = plugin._sub_task
    assert pub_task_after_shutdown is None
    assert sub_task_after_shutdown is None

    await plugin._on_startup()
    second_pub_task = plugin._pub_task
    second_sub_task = plugin._sub_task
    assert second_pub_task is not None
    assert second_sub_task is not None
    assert second_pub_task is not first_pub_task
    assert second_sub_task is not first_sub_task

    await plugin._on_shutdown()


async def test_shutdown_with_pending_messages(memory_backend: MemoryChannelsBackend) -> None:
    plugin = ChannelsPlugin(backend=memory_backend, arbitrary_channels_allowed=True)

    await plugin._on_startup()

    plugin.publish(b"message1", "test_channel")
    plugin.publish(b"message2", "test_channel")

    await asyncio.sleep(0.01)

    await plugin._on_shutdown()

    pub_task = plugin._pub_task
    sub_task = plugin._sub_task
    pub_queue = plugin._pub_queue
    assert pub_task is None
    assert sub_task is None
    assert pub_queue is None


async def test_context_manager_cleanup(memory_backend: MemoryChannelsBackend) -> None:
    plugin = ChannelsPlugin(backend=memory_backend, arbitrary_channels_allowed=True)

    async with plugin:
        pub_task_inside = plugin._pub_task
        sub_task_inside = plugin._sub_task
        pub_queue_inside = plugin._pub_queue
        assert pub_task_inside is not None
        assert sub_task_inside is not None
        assert pub_queue_inside is not None

    pub_task_outside = plugin._pub_task
    sub_task_outside = plugin._sub_task
    pub_queue_outside = plugin._pub_queue
    assert pub_task_outside is None
    assert sub_task_outside is None
    assert pub_queue_outside is None
