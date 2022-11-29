# Template Callables

Both [Jinja2](https://jinja.palletsprojects.com/en/3.0.x/) and [Mako](https://www.makotemplates.org/) allow users to define custom
callables that are ran inside the template. Starlite builds on this and offers some functions out of the box.

`url_for`
:   To access urls for route handlers you can use the `url_for` function. Its signature and behaviour
    matches [`route_reverse`][starlite.app.Starlite.route_reverse] behaviour. More details about route handler indexing
    can be found [here](../2-route-handlers/4-route-handler-indexing.md)

`csrf_token`
:   This function returns the request's unique [`csrf_token`](../7-middleware/3-builtin-middlewares/3-csrf-middleware.md). You can use this
    if you wish to insert the `csrf_token` into non-HTML based templates, or insert it into HTML templates not using a hidden input field but
    by some other means, for example inside a special `<meta>` tag.

`url_for_static_asset`
:   URLs for static files can be created using the `url_for_static_asset` function. It's signature and behaviour are identical to
    [`app.url_for_static_asset`][starlite.app.Starlite.url_for_static_asset].

## Registering Template Callables

The Starlite [`TemplateEngineProtocol`][starlite.template.base.TemplateEngineProtocol] specifies the method
`register_template_callable` that allows defining a custom callable on a template engine. This method is implemented
for the two built in engines, and it can be used to register callables that will be injected into the template. The callable
should expect one argument - the context dictionary. It can be any callable - a function, method or class that defines
the call method. For example:

```py title="template_functions.py"
--8<-- "examples/templating/template_functions.py"
```

```html title="templates/index.html.jinja2"
--8<-- "examples/templating/templates/index.html.jinja2"
```


Run the example with `uvicorn template_functions:app`, visit  http://127.0.0.1:8000, and
you'll see

![Template engine callable example](/starlite/images/examples/template_engine_callable.png)
