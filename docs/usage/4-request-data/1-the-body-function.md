# The Body Function

You can use the `Body` function to customize the OpenAPI documentation for the request body schema or to control its validation:

```python
from starlite import Body, post
from pydantic import BaseModel


class User(BaseModel):
    ...


@post(path="/user")
async def create_user(
    data: User = Body(title="Create User", description="Create a new user.")
) -> User:
    ...
```

See the [API Reference][starlite.params.Body] for full details on the `Body` function and the kwargs it accepts.
