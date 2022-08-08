# Redirect Responses

Redirect responses are [special HTTP responses](https://developer.mozilla.org/en-US/docs/Web/HTTP/Redirections) with a
status code in the 30x range.

In Starlite, a redirect response looks like this:

```python
from starlette.status import HTTP_307_TEMPORARY_REDIRECT
from starlite import get
from starlite.datastructures import Redirect


@get(path="/some-path", status_code=HTTP_307_TEMPORARY_REDIRECT)
def redirect() -> Redirect:
    # do some stuff here
    # ...
    # finally return redirect
    return Redirect(path="/other-path")
```

To return a redirect response you should do the following:

1. set an appropriate status code for the route handler (301, 302, 303, 307, 308)
2. annotate the return value of the route handler as returning `Redirect`
3. return an instance of the `Redirect` class with the desired redirect path

## The Redirect Class

`Redirect` is a container class used to generate redirect responses and their respective OpenAPI documentation. You can
pass the following kwargs to it:

- `path`: Redirection path, **required**.
- `background`: A callable wrapped in an instance of `starlette.background.BackgroundTask` or a sequence
  of `BackgroundTask` instances wrapped in `starlette.background.BackgroundTasks`. The callable(s) will be called after
  the response is executed. Note - if you return a value from a `before_request` hook, background tasks passed to the
  handler will not be executed.
- `headers`: A string/string dictionary of response headers. Header keys are insensitive.
- `cookies`: A list of `Cookie` instances. See [response-cookies](5-response-cookies.md).
