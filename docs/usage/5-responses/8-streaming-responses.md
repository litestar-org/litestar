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
