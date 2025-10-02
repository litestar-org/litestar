from __future__ import annotations

import asyncio

import pytest

from litestar.channels import ChannelsPlugin
from litestar.channels.backends.memory import MemoryChannelsBackend


async def test_shutdown_clears_task_references(memory_backend: MemoryChannelsBackend) -> None:
    """Test that _on_shutdown properly sets task references to None after cancellation."""
    plugin = ChannelsPlugin(backend=memory_backend, arbitrary_channels_allowed=True)
    
    # Start the plugin
    await plugin._on_startup()
    
    # Verify tasks are created
    assert plugin._pub_task is not None
    assert plugin._sub_task is not None
    assert plugin._pub_queue is not None
    
    # Store task references to verify they were cancelled
    pub_task = plugin._pub_task
    sub_task = plugin._sub_task
    
    # Shutdown the plugin
    await plugin._on_shutdown()
    
    # Verify tasks were cancelled
    assert pub_task.cancelled() or pub_task.done()
    assert sub_task.cancelled() or sub_task.done()
    
    # Verify task references are cleared
    assert plugin._pub_task is None, "pub_task should be None after shutdown"
    assert plugin._sub_task is None, "sub_task should be None after shutdown"
    assert plugin._pub_queue is None, "pub_queue should be None after shutdown"


async def test_shutdown_idempotent_with_task_verification(memory_backend: MemoryChannelsBackend) -> None:
    """Test that multiple shutdowns don't cause issues and tasks remain None."""
    plugin = ChannelsPlugin(backend=memory_backend, arbitrary_channels_allowed=True)
    
    # First shutdown before startup (should not raise)
    await plugin._on_shutdown()
    assert plugin._pub_task is None
    assert plugin._sub_task is None
    
    # Startup
    await plugin._on_startup()
    assert plugin._pub_task is not None
    assert plugin._sub_task is not None
    
    # First shutdown
    await plugin._on_shutdown()
    assert plugin._pub_task is None
    assert plugin._sub_task is None
    
    # Second shutdown (should not raise)
    await plugin._on_shutdown()
    assert plugin._pub_task is None
    assert plugin._sub_task is None


async def test_startup_after_shutdown_creates_new_tasks(memory_backend: MemoryChannelsBackend) -> None:
    """Test that starting up after shutdown creates new task instances."""
    plugin = ChannelsPlugin(backend=memory_backend, arbitrary_channels_allowed=True)
    
    # First lifecycle
    await plugin._on_startup()
    first_pub_task = plugin._pub_task
    first_sub_task = plugin._sub_task
    assert first_pub_task is not None
    assert first_sub_task is not None
    
    await plugin._on_shutdown()
    assert plugin._pub_task is None
    assert plugin._sub_task is None
    
    # Second lifecycle
    await plugin._on_startup()
    second_pub_task = plugin._pub_task
    second_sub_task = plugin._sub_task
    assert second_pub_task is not None
    assert second_sub_task is not None
    
    # Verify new tasks were created
    assert second_pub_task is not first_pub_task
    assert second_sub_task is not first_sub_task
    
    # Cleanup
    await plugin._on_shutdown()


async def test_shutdown_with_pending_messages(memory_backend: MemoryChannelsBackend) -> None:
    """Test that shutdown properly waits for pending messages to be published."""
    plugin = ChannelsPlugin(backend=memory_backend, arbitrary_channels_allowed=True)
    
    await plugin._on_startup()
    
    # Publish some messages
    plugin.publish(b"message1", "test_channel")
    plugin.publish(b"message2", "test_channel")
    
    # Give tasks a moment to process
    await asyncio.sleep(0.01)
    
    # Shutdown should wait for queue to be processed
    await plugin._on_shutdown()
    
    # Verify cleanup
    assert plugin._pub_task is None
    assert plugin._sub_task is None
    assert plugin._pub_queue is None


async def test_context_manager_cleanup(memory_backend: MemoryChannelsBackend) -> None:
    """Test that using the plugin as a context manager properly cleans up tasks."""
    plugin = ChannelsPlugin(backend=memory_backend, arbitrary_channels_allowed=True)
    
    async with plugin:
        # Inside context, tasks should be active
        assert plugin._pub_task is not None
        assert plugin._sub_task is not None
        assert plugin._pub_queue is not None
    
    # After context exit, tasks should be cleaned up
    assert plugin._pub_task is None
    assert plugin._sub_task is None
    assert plugin._pub_queue is None
