# Partial DTOs

For [PATCH](https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/PATCH) HTTP methods, you may only need to
partially modify a resource. In these cases, DTOs can be wrapped with [`Partial`][starlite.types.Partial].

```python
from pydantic import BaseModel
from starlite.types.partial import Partial


class CompanyDTO(BaseModel):
    id: int
    name: str
    worth: float


PartialCompanyDTO = Partial[CompanyDTO]
```

The created `PartialCompanyDTO` is equivalent to the following declaration:

```python
from typing import Optional
from pydantic import BaseModel


class PartialCompanyDTO(BaseModel):
    id: Optional[int]
    name: Optional[str]
    worth: Optional[float]
```

[`Partial`][starlite.types.Partial] can also be used inline when creating routes.

```python
from pydantic import UUID4, BaseModel
from starlite.controller import Controller
from starlite.handlers import patch
from starlite.types.partial import Partial


class UserOrder(BaseModel):
    order_id: UUID4
    order_item_id: UUID4
    notes: str


class UserOrderController(Controller):
    path = "/user"

    @patch(path="/{order_id:uuid}")
    async def update_user_order(
        self, order_id: UUID4, data: Partial[UserOrder]
    ) -> UserOrder:
        ...
```
