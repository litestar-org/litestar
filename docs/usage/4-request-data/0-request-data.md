# Request Data

For http requests except `GET` requests, you can access the request body by specifying the `data` kwarg in your
handler function or method:

```python
from starlite import post
from pydantic import BaseModel


class User(BaseModel):
    ...


@post(path="/user")
async def create_user(data: User) -> User:
    ...
```

The type of `data` does not need to be a pydantic model - it can be any supported type, e.g. a dataclass, or a `TypedDict`:

```python
from starlite import post
from dataclasses import dataclass


@dataclass()
class User:
    ...


@post(path="/user")
async def create_user(data: User) -> User:
    ...
```

It can also be simple types such as `str`, `dict` etc. or classes supported by [plugins](../10-plugins/0-plugins-intro.md).
