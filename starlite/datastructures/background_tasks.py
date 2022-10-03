from typing import Any, Callable, List, TypeVar

from starlette.background import BackgroundTask as StarletteBackgroundTask
from starlette.background import BackgroundTasks as StarletteBackgroundTasks
from typing_extensions import ParamSpec

P = ParamSpec("P")
T = TypeVar("T")


class BackgroundTask(StarletteBackgroundTask):
    def __init__(self, func: Callable[P, Any], *args: P.args, **kwargs: P.kwargs) -> None:
        """A container for a 'background' task function. Background tasks are
        called once a Response finishes.

        Args:
            func: A sync or async function to call as the background task.
            *args: Args to pass to the func.
            **kwargs: Kwargs to pass to the func
        """
        super().__init__(func, *args, **kwargs)


class BackgroundTasks(StarletteBackgroundTasks):
    def __init__(self, tasks: List[BackgroundTask]) -> None:
        """A container for multiple 'background' task functions. Background
        tasks are called once a Response finishes.

        Args:
            tasks: A list of [BackgroundTask][starlite.datastructures.BackgroundTask] instances.
        """
        super().__init__(tasks=tasks)
