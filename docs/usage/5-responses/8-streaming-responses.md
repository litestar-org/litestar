# Streaming Responses

To return a streaming response use the `Stream` class. The Stream class receives a single required kwarg - `iterator`:

```python
from typing import AsyncGenerator
from asyncio import sleep
from starlite import Stream, get
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

`Stream` is a container class used to generate streaming responses and their respective OpenAPI documentation.
See the [API Reference][starlite.datastructures.Stream] for full details on the `Stream` class and the kwargs it accepts.
