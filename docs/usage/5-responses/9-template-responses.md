# Template Responses

Template responses are used to render templates into HTML. To use a template response you must first register
a [template engine](../16-templating#template-engines) on the application level. Once an engine is in place, you can use a template
response like so:

```python
from starlite import Template, Request, get


@get(path="/info")
def info(request: Request) -> Template:
    return Template(name="info.html", context={"user": request.user})
```

In the above `Template` is passed the template name, which is a path like value, and a context dictionary that maps
string keys into values that will be rendered in the template.

## The Template Class

`Template` is a container class used to generate template responses and their respective OpenAPI documentation.
See the [API Reference][starlite.datastructures.Template] for full details on the `Template` class and the kwargs it accepts.
