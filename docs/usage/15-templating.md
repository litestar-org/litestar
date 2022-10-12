# Templating

Starlite has built-in support for both [jinja2](https://jinja.palletsprojects.com/en/3.0.x/)
and [mako](https://www.makotemplates.org/) as template engines, and it also offers a simple way to add additional
template engines.

## Registering a Template Engine

To register one of the built-in template engines you simply need to pass it to the Starlite constructor:

```python
from starlite import TemplateConfig, Starlite
from starlite.template.jinja import JinjaTemplateEngine

app = Starlite(
    route_handlers=[...],
    template_config=TemplateConfig(directory="templates", engine=JinjaTemplateEngine),
)
```

Or

```python
from starlite import TemplateConfig, Starlite
from starlite.template.mako import MakoTemplateEngine

app = Starlite(
    route_handlers=[...],
    template_config=TemplateConfig(directory="templates", engine=MakoTemplateEngine),
)
```

The kwarg `directory` passed to `TemplateConfig` is either a directory or list of directories to use for loading
templates.

## Template Responses

Once you have a template engine registered you can use it in route handlers:

```python
from starlite import Template, Request, get


@get(path="/info")
def info(request: Request) -> Template:
    return Template(name="info.html", context={"user": request.user})
```

The `name` kwarg passed to the `Template` class is the filename for the given template. Starlite will search all the
directories specifies for this file until it finds it or an exception will be raised. The `context` kwarg is a
dictionary specifying context data that is passed to the engine.

Starlite automatically injects current request into context under `request` name. Note that if you try pass any value
under `request` key it will be overridden with the current request.

URLs for indexed route handlers in templates can be generated with `url_for` function available both in Jinja2 and Mako
templates. Its signature and behaviour matches [`route_reverse`][starlite.app.Starlite.route_reverse] behaviour.
More details about rout handler indexing can be found [here](2-route-handlers/4-route-handler-indexing.md)

## Defining a Custom Template Engine

If you wish to use another templating engine, you can easily do so by
implementing `starlite.template.TemplateEngineProtocol`. This class accepts a generic argument `T` which should be the
template class, and it specifies two methods:

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

## Modifying the Template Engine Instance

`TemplateConfig` accepts the `engine_callback` keyword arg which provides a way to modify the instantiated
template engine instance. For example:

```python
from starlite import TemplateConfig
from starlite.template.jinja import JinjaTemplateEngine


def engine_callback(jinja_engine: JinjaTemplateEngine) -> JinjaTemplateEngine:
    jinja_engine.engine.globals["key"] = "value"
    return jinja_engine


template_config = TemplateConfig(
    directory="templates", engine=JinjaTemplateEngine, engine_callback=engine_callback
)
```

The callback should receive a single argument which will be the instantiated engine, and must
return the instantiated engine.
