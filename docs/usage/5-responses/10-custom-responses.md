# Custom Responses

TODO (old text below)

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

It would be best if we had a generic response class that was able to handle all `Document` subclasses. Luckily,
the `Document` model already comes with a `to_dict` method, which makes our lives a bit simpler:

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
