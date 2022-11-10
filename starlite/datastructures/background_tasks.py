from typing import Any, Callable, Iterable

from anyio import create_task_group
from typing_extensions import ParamSpec

from starlite.utils.sync import AsyncCallable

P = ParamSpec("P")


class BackgroundTask:
    """A container for a 'background' task function.

    Background tasks are called once a Response finishes.
    """

    __slots__ = ("fn", "args", "kwargs")

    def __init__(self, fn: Callable[P, Any], *args: P.args, **kwargs: P.kwargs) -> None:
        """Initialize `BackgroundTask`.

        Args:
            fn: A sync or async function to call as the background task.
            *args: Args to pass to the func.
            **kwargs: Kwargs to pass to the func
        """
        self.fn = AsyncCallable(fn)
        self.args = args
        self.kwargs = kwargs

    async def __call__(self) -> None:
        """Call the wrapped function with the passed in arguments.

        Returns:
            None
        """
        await self.fn(*self.args, **self.kwargs)


class BackgroundTasks:
    """A container for multiple 'background' task functions.

    Background tasks are called once a Response finishes.
    """

    __slots__ = ("tasks", "run_in_task_group")

    def __init__(self, tasks: Iterable[BackgroundTask], run_in_task_group: bool = False) -> None:
        """Initialize `BackgroundTasks`.

        Args:
            tasks: An iterable of [BackgroundTask][starlite.datastructures.BackgroundTask] instances.
            run_in_task_group: If you set this value to `True` than the tasks will run concurrently, using
                an [anyio.task_group](https://anyio.readthedocs.io/en/stable/tasks.html). Note: this will
                not preserve execution order.
        """
        self.tasks = tasks
        self.run_in_task_group = run_in_task_group

    async def __call__(self) -> None:
        """Call the wrapped background tasks.

        Returns:
            None
        """
        if self.run_in_task_group:
            async with create_task_group() as task_group:
                for task in self.tasks:
                    task_group.start_soon(task)
        else:
            for task in self.tasks:
                await task()
