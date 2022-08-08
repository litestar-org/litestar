# Overriding Dependencies

Because dependencies are declared at each level of the app using a string keyed dictionary, overriding dependencies is
very simple:

```python
from starlite import Controller, Provide, get


def bool_fn() -> bool:
    ...


def dict_fn() -> dict:
    ...


class MyController(Controller):
    path = "/controller"
    # on the controller
    dependencies = {"some_dependency": Provide(dict_fn)}

    # on the route handler
    @get(path="/handler", dependencies={"some_dependency": Provide(bool_fn)})
    def my_route_handler(
        self,
        some_dependency: bool,
    ) -> None:
        ...
```

The lower scoped route handler function declares a dependency with the same key as the one declared on the higher scoped
controller. The lower scoped dependency therefore overrides the higher scoped one.
