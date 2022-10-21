# Template Callables

Both `Jinja` and `Mako` allow users to define custom callables that are ran inside the template. Starlite builds on this
and offers some functions out of the box.

## The `url_for` Callable

To access urls for route handlers you can use the `url_for` function. Its signature and behaviour
matches [route_reverse][starlite.app.Starlite.route_reverse] behaviour. More details about route handler indexing
can be found [here](../2-route-handlers/4-route-handler-indexing.md)

## The `csrf_token` Callable

This function returns the request's unique `csrf_token`. You can use this if you wish to insert the `csrf_token` into
non-HTML based templates, or insert it into HTML templates not using a hidden input field but by some other means,
for example inside a special `<meta>` tag.

## The `url_for_static_asset` Callable

URLs for static files can be created using the `url_for_static_asset` function. It's signature and behaviour are identical to
[app.url_for_static_asset][starlite.app.Starlite.url_for_static_asset].

## Registering Template Callables

The Starlite [TemplateEngineProtocol][starlite.template.base.TemplateEngineProtocol] specifies the method
`register_template_callable` that allows defining a custom callable on a template engine. This method is implemented
for the two built in engine, and it can be used to register callables that will be inject on the template. The callable
should expect one argument - the context dictionary. It can be any callable - a function, method or class that defines
the call method. For example:

```python
from starlite import TemplateConfig, Starlite
from starlite.template.mako import MakoTemplateEngine

template_config = TemplateConfig(directory="templates", engine=MakoTemplateEngine)


def my_template_function(ctx: dict) -> str:
    return ctx.get("my_context_key", "nope")


template_config.engine.register_template_callable(
    "check_context_key", template_callable=my_template_function
)

app = Starlite(
    route_handlers=[...],
    template_config=template_config,
)
```

The above example defined the function `my_template_function` as a callable inside the template that can be called using
the key `check_context_key`. Using the `Jinja` syntax this will be:

```text
{{check_context_key}}
```

And using `Mako`

```text
${check_context_key}
```
