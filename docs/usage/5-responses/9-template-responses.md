# Template Responses

Template responses are used to render templates into HTML. To use a template response you must first register
a [template engine](../15-templating.md) on the application level. Once an engine is in place, you can use a template
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

`Template` is a container class used to generate template responses and their respective OpenAPI documentation. You can
pass the following kwargs to it:

- `name`: Path-like name for the template to be rendered, **required**.
- `context`: "A dictionary of key/value pairs to be passed to the temple engine's render method.
- `background`: A callable wrapped in an instance of `starlite.datastructures.BackgroundTask` or a list
  of `BackgroundTask` instances wrapped in `starlite.datastructures.BackgroundTasks`. The callable(s) will be called after
  the response is executed. Note - if you return a value from a `before_request` hook, background tasks passed to the
  handler will not be executed.
- `headers`: A string/string dictionary of response headers. Header keys are insensitive.
- `cookies`: A list of `Cookie` instances. See [response-cookies](5-response-cookies.md).
