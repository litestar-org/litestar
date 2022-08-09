# Custom Responses

You can use a subclass of `starlite.responses.Response` and specify it as the response class using the `response_class`
kwarg.

For example, lets say we want to handle subclasses of `Document` from the `elasticsearch_dsl` package as shown below:

```python
from elasticsearch_dsl import Document, Integer, Keyword


class MyDocument(Document):
    name = Keyword()
    level = Integer()
    type = Keyword()
```

The `Document` class is not JSON serializable on its own, and as such we cannot simply return it from a route handler
function and expect it to be serialized.

We could of course convert it to a dictionary of values in the route handler, and then use it. But if we
return `Document` subclasses in many route handlers, it makes sense to create a custom response to handle the
serialization.

We will therefore create a subclass of `starlite.response.Response` that implements a serializer method that is capable
of handling `Document` subclasses:

```python
from typing import Any, Dict

from elasticsearch_dsl import Document
from starlite import Response


class DocumentResponse(Response):
    def serializer(self, value: Any) -> Dict[str, Any]:
        if isinstance(value, Document):
            return value.to_dict()
        return super().serializer(value)
```

We can now use this in our route handler:

```python
from elasticsearch_dsl import Document
from starlite import get

from my_app.responses import DocumentResponse


@get(path="/document", response_class=DocumentResponse)
def get_document() -> Document:
    ...
```

You can specify the response class to use at all levels of your application. On specific route handlers, on a
controller, a router even on the app instance itself:

```python
from starlite import Controller, Starlite, Router

from my_app.responses import DocumentResponse


# controller
class MyController(Controller):
    path = "..."
    response_class = DocumentResponse


# router
my_router = Router(path="...", route_handlers=[...], response_class=DocumentResponse)

# app
my_app = Starlite(route_handlers=[...], response_class=DocumentResponse)
```

When you specify a response_class in multiple places, the closest layer to the response handler will take precedence.
That is, the `response_class` specified on the route handler takes precedence over the one specified on the controller
or router, which will in turn take precedence over the one specified on the app level. You can therefore easily override
response classes as needed.
