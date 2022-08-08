# Streaming Responses

To return a streaming response use the `Stream` class:

```python
from asyncio import sleep
from starlite import get
from starlite.datastructures import Stream
from datetime import datetime
from orjson import dumps


async def my_iterator() -> bytes:
    while True:
        await sleep(0.01)
        yield dumps({"current_time": datetime.now()})


@get(path="/time")
def stream_time() -> Stream:
    return Stream(iterator=my_iterator)
```

The Stream class receives a single required kwarg - `iterator`, which should be either a sync or an async iterator.

## The Stream Class

`Stream` is a container class used to generate streaming responses and their respective OpenAPI documentation. You can
pass the following kwargs to it:

- `iterator`: An either, either sync or async, that handles streaming data, **required**.
- `background`: A callable wrapped in an instance of `starlette.background.BackgroundTask` or a sequence
  of `BackgroundTask` instances wrapped in `starlette.background.BackgroundTasks`. The callable(s) will be called after
  the response is executed. Note - if you return a value from a `before_request` hook, background tasks passed to the
  handler will not be executed.
- `headers`: A string/string dictionary of response headers. Header keys are insensitive.
- `cookies`: A list of `Cookie` instances. See [response-cookies](5-response-cookies.md).
