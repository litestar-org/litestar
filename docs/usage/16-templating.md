# Templates

## Template engines

Starlite has built-in support for both [Jinja2](https://jinja.palletsprojects.com/en/3.0.x/)
and [Mako](https://www.makotemplates.org/) as template engines, and it also offers a simple way to add additional
template engines.

### Registering a Template Engine

To register one of the built-in template engines you simply need to pass it to the Starlite constructor:

=== "Jinja"
    ```python
    --8 < --"examples/templating/template_engine_jinja.py"
    ```

=== "Mako"
    ```python
    --8 < --"examples/templating/template_engine_mako.py"
    ```

!!! info
    The `directory` parameter passed to [`TemplateConfig`][starlite.config.template.TemplateConfig]
    can be either a directory or list of directories to use for loading templates.

## Template Responses

Once you have a template engine registered you can return [`Template`s][starlite.Template] from
your route handlers:

=== "Jinja"
    ```python
    --8 < --"examples/templating/returning_templates_jinja.py"
    ```

=== "Mako"
    ```python
    --8 < --"examples/templating/returning_templates_mako.py"
    ```

- `name` is the name of the template file within on of the specified directories. If
no file with that name is found, a [`TemplateNotFoundException`][starlite.exceptions.TemplateNotFoundException]
exception will be raised.
- `context` is a dictionary containing arbitrary data that will be passed to the template
engine's `render` method. For *Jinja* and *Mako*, this data will be available in the [template context](#template-context)

### Defining a Custom Template Engine

If you wish to use another templating engine, you can easily do so by implementing
[`TemplateEngineProtocol`][starlite.template.TemplateEngineProtocol]. This class accepts a generic
argument `T` which should be the template class, and it specifies two methods:

```python
from typing import Protocol, Union, List
from pydantic import DirectoryPath

# the template class of the respective library
from some_lib import SomeTemplate


class TemplateEngineProtocol(Protocol[SomeTemplate]):
    def __init__(self, directory: Union[DirectoryPath, List[DirectoryPath]]) -> None:
        """Builds a template engine."""
        ...

    def get_template(self, template_name: str) -> SomeTemplate:
        """Loads the template with template_name and returns it."""
        ...
```

Once you have your custom engine you can register it as you would the built-in engines.

### Accessing the Template Engine instance

If you need to access the template engine instance, you can do so via the
[`TemplateConfig.engine`][starlite.config.template.TemplateConfig] attribute:

```python
--8 < --"examples/templating/engine_instance.py"
```


## Template Context

Both [Jinja2](https://jinja.palletsprojects.com/en/3.0.x/) and [Mako](https://www.makotemplates.org/) support passing a context
object to the template as well as defining callables that will be available inside the template.

### Accessing the request instance

The current [`Request`][starlite.connection.request.Request] is available within the
template context under `request`, which also provides access to the [app instance](/starlite/usage/the-starlite-app).

Accessing `app.state.key` for example would look like this:

=== "Jinja"
    ```html
    <html>
        <body>
            <div>
                <span>My state value: {{request.app.state.some_key}}</span>
            </div>
        </body>
    </html>
    ```

=== "Mako"
    ```html
    <html>
        <body>
            <div>
                <span>My state value: ${request.app.state.some_key}</span>
            </div>
        </body>
    </html>
    ```

### Adding CSRF Inputs

If you want to add a hidden `<input>` tag containing a
[CSRF token](https://developer.mozilla.org/en-US/docs/Web/Security/Types_of_attacks#cross-site_request_forgery_csrf),
you first need to configure [CSRF protection](/starlite/usage/7-middleware/3-builtin-middlewares/3-csrf-middleware.md).
With that in place, you can now insert the CSRF input field inside an HTML form:

=== "Jinja"
    ```html
    <html>
        <body>
            <div>
                <form action="https://myserverurl.com/some-endpoint" method="post">
                    {{ csrf_input }}
                    <label for="fname">First name:</label><br>
                    <input type="text" id="fname" name="fname">
                    <label for="lname">Last name:</label><br>
                    <input type="text" id="lname" name="lname">
                </form>
            </div>
        </body>
    </html>
    ```

=== "Mako"
    ```html
    <html>
        <body>
            <div>
                <form action="https://myserverurl.com/some-endpoint" method="post">
                    ${csrf_input}
                    <label for="fname">First name:</label><br>
                    <input type="text" id="fname" name="fname">
                    <label for="lname">Last name:</label><br>
                    <input type="text" id="lname" name="lname">
                </form>
            </div>
        </body>
    </html>
    ```

The input is hidden so users cannot see and interact with it. It will though be sent back to the server when submitted,
and the CSRF middleware will check that the token is valid.

### Passing Template Context

Passing context to the template is very simple - its one of the kwargs expected by the [`Template`][starlite.response.TemplateResponse]
container, so simply pass a string keyed dictionary of values:

```python
from starlite import Template, get


@get(path="/info")
def info() -> Template:
    return Template(name="info.html", context={"numbers": "1234567890"})
```


## Template Callables

Both [Jinja2](https://jinja.palletsprojects.com/en/3.0.x/) and [Mako](https://www.makotemplates.org/) allow users to define custom
callables that are ran inside the template. Starlite builds on this and offers some functions out of the box.

`url_for`:   To access urls for route handlers you can use the `url_for` function. Its signature and behaviour
    matches [`route_reverse`][starlite.app.Starlite.route_reverse] behaviour. More details about route handler indexing
    can be found [here](/starlite/usage/2-route-handlers/4-route-handler-indexing.md)

`csrf_token`:   This function returns the request's unique [`csrf_token`](/starlite/usage/7-middleware/3-builtin-middlewares/3-csrf-middleware.md). You can use this
    if you wish to insert the `csrf_token` into non-HTML based templates, or insert it into HTML templates not using a hidden input field but
    by some other means, for example inside a special `<meta>` tag.

`url_for_static_asset`:   URLs for static files can be created using the `url_for_static_asset` function. It's signature and behaviour are identical to
    [`app.url_for_static_asset`][starlite.app.Starlite.url_for_static_asset].

### Registering Template Callables

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
