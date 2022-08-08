# The Dependency Function

Starlite infers function parameters to be provided dependencies if there is a `Provide` anywhere in the handler's
ownership tree keyed to the same name as the function parameter. Other parameters are either reserved kwargs or query,
cookie or header parameters.

This works well, except when a dependency is optional. For example, consider the following:

```python
from typing import NamedTuple, Optional
from starlite import Provide, get, post
from pydantic import BaseModel


class LimitOffset(NamedTuple):
    limit: int
    offset: int


class Resource(BaseModel):
    id: int
    ...


class ResourceRepository:
    def __init__(self, limit_offset: Optional[LimitOffset] = None) -> None:
        ...

    async def retrieve_resources(self) -> list[Resource]:
        ...

    async def create_resource(self, data: Resource) -> Resource:
        ...


# limit and offset are optional query parameters here
def limit_offset_filter(limit: int = 100, offset: int = 0) -> LimitOffset:
    return LimitOffset(limit, offset)


@post(dependencies={"repository": Provide(ResourceRepository)})
async def create_resource(data: Resource, repository: ResourceRepository) -> Resource:
    return await repository.create_resource(data=data)


@get(
    dependencies={
        "limit_offset": Provide(limit_offset_filter),
        "repository": Provide(ResourceRepository),
    }
)
async def get_resource(repository: ResourceRepository) -> list[Resource]:
    return await repository.retrieve_resources()
```

This configuration works, however, `limit_offset` from the `ResourceRepository` will appear as a `query` parameter in
the OpenAPI documentation for `create_resource` because Starlite cannot ascertain it is a dependency in this case.
To resolve this, we mark the parameter `limit_offset` with the `Dependency` function:

```python
from typing import Optional, NamedTuple
from starlite import Dependency


class LimitOffset(NamedTuple):
    limit: int
    offset: int


class ResourceRepository:
    def __init__(
        self, limit_offset: Optional[LimitOffset] = Dependency(default=None)
    ) -> None:
        ...
```

Now Starlite knows that the function parameter is not a `query` parameter and that it should not appear in the OpenAPI
documentation.

`Dependency` accepts a single kwarg - `default`, which is the default value for the parameter, if any.
