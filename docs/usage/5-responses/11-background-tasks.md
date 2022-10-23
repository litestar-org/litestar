# Background Tasks

All Starlite responses and response containers (e.g. `File`, `Template` etc.) allow passing in a `background_task`
kwarg. This kwarg accepts either an instance of [BackgroundTask][starlite.datastructures.background_tasks.BackgroundTask]
or
an instance of [BackgroundTasks][starlite.datastructures.background_tasks.BackgroundTasks], which wraps an iterable
of [BackgroundTask][starlite.datastructures.background_tasks.BackgroundTask] instances.

A background task is a sync or async callable (function, method or class that implements the `__call__` dunder method)
that will be called after the response finishes sending the data.

Thus, in the following example the passed in background task will be executed after the response sends:

```python
import logging

from starlite import BackgroundTask, get

logger = logging.getLogger(__name__)


async def logging_task(identifier: str, message: str) -> None:
    logger.info(f"{identifier}: {message}")


@get("/", background=BackgroundTask(logging_task, "greeter", message="was called"))
def greeter() -> dict[str, str]:
    return {"hello": "world"}
```

When the `greeter` handler is called, the logging task will be called with any `*args` and `**kwargs` passed into the
`BackgroundTask`.

!!! note
In the above example `"greeter"` is an arg and `message="was called"` is a kwarg. The function signature of
`logging_task` allows for this, so this should pose no problem. Starlite uses [ParamSpec][typing.ParamSpec] to ensure
that a [BackgroundTask][starlite.datastructures.background_tasks.BackgroundTask] is properly typed, so will get
type checking for any passed in args and kwargs.

## Executing Multiple BackgroundTasks

You can also use the [BackgroundTasks][starlite.datastructures.background_tasks.BackgroundTasks] class instead, and pass
to it an iterable (list, tuple etc.) of [BackgroundTask][starlite.datastructures.background_tasks.BackgroundTask]
instances. This class accepts one optional kwargs aside from the tasks - `run_in_task_group`, which is a boolean flag
that defaults to `False`. If you set this value to `True` than the tasks will run concurrently, using
an [anyio.task_group](https://anyio.readthedocs.io/en/stable/tasks.html).

!!! note
    Setting `run_in_task_group` to `True` will not preserve execution order.
