# Query Parameters

To define query parameters simply define them as kwargs in your function declaration:

```python
from datetime import datetime
from typing import Optional

from starlite import get
from pydantic import BaseModel


class Order(BaseModel):
    ...


@get(path="/orders")
def get_orders(
    page: int,
    brands: list[str],
    page_size: int = 10,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
) -> list[Order]:
    ...
```

The above is a rather classic example of a paginated "GET" request:

1. _page_ is a required query parameter of type `int`. It has no default value and as such has to be provided or a
   ValidationException will be raised.
2. _page_size_ is a required query parameter of type `int` as well, but it has a default value - so it can be omitted in
   the request.
3. _brands_ is an optional list of strings with a default `None` value.
4. _from_date_ and _to_date_ are optional date-time values that have a default `None` value.

These parameters will be parsed from the function signature and used to generate a pydantic model. This model in turn
will be used to validate the parameters and generate the OpenAPI schema.

This means that you can also use any pydantic type in the signature, and it will follow the same kind of validation and
parsing as you would get from pydantic.

This works great, but what happens when the request is sent with a non-python naming scheme, such as _camelCase_? You
could of course simply rename your variables accordingly:

```python
from datetime import datetime
from typing import Optional

from starlite import get
from pydantic import BaseModel


class Order(BaseModel):
    ...


@get(path="/orders")
def get_orders(
    page: int,
    brands: list[str],
    pageSize: int = 10,
    fromDate: Optional[datetime] = None,
    toDate: Optional[datetime] = None,
) -> list[Order]:
    ...
```

This doesn't look so good, and tools such as PyLint will complain. The solution here is to
use [the Parameter function](./3-the-parameter-function.md):

```python
from datetime import datetime
from typing import Optional

from starlite import get, Parameter
from pydantic import BaseModel


class Order(BaseModel):
    ...


@get(path="/orders")
def get_orders(
    page: int,
    page_size: int = Parameter(query="pageSize", gt=0, le=100),
    brands: list[str] = Parameter(min_items=2, max_items=5),
    from_Date: Optional[datetime] = Parameter(query="fromDate"),
    to_date: Optional[datetime] = Parameter(query="fromDate"),
) -> list[Order]:
    ...
```

As you can see, specifying the "query" kwarg allows us to remap from one key to another. Furthermore, we can use
Parameter for extended validation and documentation, as is done for `page_size`.
