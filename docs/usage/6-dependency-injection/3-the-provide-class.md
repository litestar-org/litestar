# The Provide Class

The class `starlite.provide.Provide` is a wrapper used for dependency injection. To inject a callable you must wrap it
in `Provide`:

```python
from starlite import Provide, get
from random import randint


def my_dependency() -> int:
    return randint(1, 10)


@get(
    "/some-path",
    dependencies={
        "my_dep": Provide(
            my_dependency,
        )
    },
)
def my_handler(my_dep: int) -> None:
    ...
```

`Provide` receives the following parameters:

- `dependency`: **required**, a callable function, method or class to be injected as a dependency. This parameter can be
  provided as either an arg or a kwarg.
- `use_cache`: boolean flag dictating whether to cache the return value of the dependency. Defaults to False.
- `sync_to_thread`: boolean flag dictating whether to run sync dependencies in an async thread. Defaults to False.

!!! important
    If `Provide.use_cache` is true, the return value of the function will be memoized the first time it is called and
    then will be used. There is no sophisticated comparison of kwargs, LRU implementation etc. so you should be careful
    when you choose to use this option.
