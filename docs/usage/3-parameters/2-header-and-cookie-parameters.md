# Header and Cookie Parameters

Unlike _Query_ parameters, _Header_ and _Cookie_ parameters have to be declared using
[the Parameter function](3-the-parameter-function.md), for example:

```python
from pydantic import UUID4
from starlite import get, Parameter
from pydantic import BaseModel


class User(BaseModel):
    ...


@get(path="/users/{user_id:uuid}/")
async def get_user(
    user_id: UUID4,
    token: str = Parameter(header="X-API-KEY"),
    cookie: str = Parameter(cookie="my-cookie-param"),
) -> User:
    ...
```

As you can see in the above, header parameters are declared using the `header` kwargs and cookie parameters using
the `cookie` kwarg. Aside form this difference they work the same as query parameters.
