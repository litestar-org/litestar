# The Provide Class

The class `starlite.datastructures.Provide` is a wrapper used for dependency injection. To inject a callable you must wrap it
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

See the [API Reference][starlite.datastructures.Provide] for full details on the `Provide` class and the kwargs it accepts.

!!! important
    If `Provide.use_cache` is true, the return value of the function will be memoized the first time it is called and
    then will be used. There is no sophisticated comparison of kwargs, LRU implementation etc. so you should be careful
    when you choose to use this option.
