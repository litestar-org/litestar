# Background Tasks

All Starlite responses and response containers (e.g. `File`, `Template`, etc.) allow passing in a `background`
kwarg. This kwarg accepts either an instance of [`BackgroundTask`][starlite.datastructures.background_tasks.BackgroundTask]
or an instance of [`BackgroundTasks`][starlite.datastructures.background_tasks.BackgroundTasks], which wraps an iterable
of [`BackgroundTask`][starlite.datastructures.background_tasks.BackgroundTask] instances.

A background task is a sync or async callable (function, method or class that implements the `__call__` dunder method)
that will be called after the response finishes sending the data.

Thus, in the following example the passed in background task will be executed after the response sends:

```py title="Background Task Passed into Response"
--8<-- "examples/responses/background_tasks_1.py"
```

When the `greeter` handler is called, the logging task will be called with any `*args` and `**kwargs` passed into the
`BackgroundTask`.

!!! note
    In the above example `"greeter"` is an arg and `message=f"was called with name {name}"` is a kwarg.
    The function signature of `logging_task` allows for this, so this should pose no problem.
    [`BackgroundTask`][starlite.datastructures.background_tasks.BackgroundTask] is typed with [`ParamSpec`][typing.ParamSpec], enabling correct type checking for arguments and keyword arguments passed to it.

Route decorators (e.g. `@get`, `@post`, etc.) also allow passing in a background task with the `background` kwarg:

```py title="Background Task Passed into Decorator"
--8<-- "examples/responses/background_tasks_2.py"
```

!!! note
    Route handler arguments cannot be passed into background tasks when they are passed into decorators.

## Executing Multiple Background Tasks

You can also use the [`BackgroundTasks`][starlite.datastructures.background_tasks.BackgroundTasks] class and pass
to it an iterable (list, tuple, etc.) of [`BackgroundTask`][starlite.datastructures.background_tasks.BackgroundTask]
instances:

```py title="Multiple Background Tasks"
--8<-- "examples/responses/background_tasks_3.py"
```

[`BackgroundTasks`][starlite.datastructures.background_tasks.BackgroundTasks] class
accepts an optional keyword argument `run_in_task_group` with a default value of `False`. Setting this to `True` allows background tasks to run concurrently, using an [`anyio.task_group`](https://anyio.readthedocs.io/en/stable/tasks.html). 

!!! note
    Setting `run_in_task_group` to `True` will not preserve execution order.
