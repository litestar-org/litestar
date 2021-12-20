# Parameters

## Path Parameters

Defining path parameters is straightforward:

```python
from starlite import get


@get(path="/user/{user_id:int}")
def get_user(user_id: int):
    ...
```

In the above there are two components:

First, the path parameter is defined inside the `path` kwarg passed to the _@get_ decorator inside curly brackets and
following the form `{parameter_name:parameter_type}`. This definition of the path parameter is based on
the [Starlette path parameter](https://www.starlette.io/routing/#path-parameters)
mechanism. Yet, in difference to Starlette, which allows defining path parameters without defining their types, StarLite
enforces this typing, with the following types supported: _int_, _float_, _str_, _uuid_.

Second, the `get_user` function defines a parameter with the same name as defined in the `path` kwarg. This ensures that
the value of the path parameter will be injected into the function when it's called.

The types do not need to match 1:1 - as long as you type your parameter inside the function declaration with a high type
this should be ok. For example, consider this:

```python
from datetime import datetime

from starlite import get


@get(path="/orders/{from_date:int}")
def get_orders(from_date: datetime):
    ...
```

The parameter defined inside the `path` kwarg is typed as int, because the value passed from the frontend will be a
timestamp in milliseconds. The parameter in the function declaration though is typed as `datetime.datetime`. This is
fine- the int value will be passed to a pydantic model representing the function signature, which will coerce the int
into a datetime. Thus, when the function is called it will be called with a datetime typed parameter.

Finally, you should note that you only need to define the parameter in the function declaration if it's actually used
inside the function. If the path parameter is part of the path, but you do not actually need to use it in your business
logic, it's fine to omit it from the function declaration - it will still be validated and added to the openapi schema
correctly.

## Query Parameters

To define query parameters simply define them as `kwargs` in your function declaration:

```python
from datetime import datetime
from typing import List, Optional, Union

from starlite import get


@get(path="/orders")
def get_orders(
        page: int,
        brands: List[str],
        page_size: int = 10,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
):
    ...
```

The above example is a rather classic example of a paginated get request:

1. _page_ is a required query parameter of type int. It has no default value and as such has to be given.
2. _page_size_ is a required query parameter of type int as well, but it has a default value - so it can be omitted in
   the request.
3. _brands_ is an optional list of strings with a default None value.
4. _from_date_ and _to_date_ or optional date-time values that have a default None value.

These parameters will be parsed from the function signature and used to generate a pydantic model. This model in turn
will be used to validate the parameters, and also to generate the OpenAPI schema for this endpoint.

This means that you can also use any pydantic type in the signature, and it will follow the same kind of validation and
parsing as you would get from pydantic.

Let's leverage this to make our query parameters more precise - which, by and by, will also make the OpenAPI schema more
precise:

```python
from datetime import datetime
from typing import List, Optional

from starlite import get
from pydantic import conlist, conint


@get(path="/orders")
def get_orders(
        page: int,
        page_size: int = conint(gt=0, le=100),
        brands: List[str] = conlist(str, min_items=1, max_items=3),
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
):
    ...
```

In the above we use the pydantic methods `conlist` and `conint` to constrict the values for _page_size_ and _brands_:
page_size must be greater than 0 and less than or equal to 100. Brands can be None, or a list of minimum 1 and maximum 3
items. If we wanted to ensure these are unique, we would have used `conset` instead of `conlist`.


## Header Parameters
