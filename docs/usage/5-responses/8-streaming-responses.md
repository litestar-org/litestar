# Streaming Responses

To return a streaming response use the `Stream` class. The Stream class receives a single required kwarg - `iterator`:

```python
from typing import AsyncGenerator
from asyncio import sleep
from starlite import get
from starlite.datastructures import Stream
from datetime import datetime
from orjson import dumps


async def my_generator() -> AsyncGenerator[bytes, None]:
    while True:
        await sleep(0.01)
        yield dumps({"current_time": datetime.now()})


@get(path="/time")
def stream_time() -> Stream:
    return Stream(iterator=my_generator())
```

!!! note
    You can use different kinds of values of the `iterator` keyword - it can be a callable returning a sync or async
    generator. The generator itself. A sync or async iterator class, or and instance of this class.

## The Stream Class

`Stream` is a container class used to generate streaming responses and their respective OpenAPI documentation. You can
pass the following kwargs to it:

- `iterator`: A sync or async iterator instance, iterator class, generator or callable returning a generator, **required**.
- `background`: A callable wrapped in an instance of `starlite.datastructures.BackgroundTask` or a list
  of `BackgroundTask` instances wrapped in `starlite.datastructures.BackgroundTasks`. The callable(s) will be called after
  the response is executed. Note - if you return a value from a `before_request` hook, background tasks passed to the
  handler will not be executed.
- `headers`: A string/string dictionary of response headers. Header keys are insensitive.
- `cookies`: A list of `Cookie` instances. See [response-cookies](5-response-cookies.md).
