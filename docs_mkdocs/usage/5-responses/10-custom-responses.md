# Custom Responses

While Starlite supports the serialization of many types by default, sometimes you
want to return something that's not supported. In those cases it's convenient to make
use of a custom response class.

The example below illustrates how to deal with [MultiDict][starlite.datastructures.MultiDict]
instances.

```py
--8<-- "examples/responses/custom_responses.py"
```

!!! info "Layered architecture"
    Response classes are part of Starlite's layered architecture, which means you can
    set a response class on every layer of the application. If you have set a response
    class on multiple layers, the layer closes to the route handler will take precedence.

    You can read more about this here:
    [Layered architecture](/starlite/usage/0-the-starlite-app#layered-architecture)
