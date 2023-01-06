# Redirect Responses

Redirect responses are [special HTTP responses](https://developer.mozilla.org/en-US/docs/Web/HTTP/Redirections) with a
status code in the 30x range.

In Starlite, a redirect response looks like this:

```python
from starlite.status_codes import HTTP_307_TEMPORARY_REDIRECT
from starlite import Redirect, get


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

`Redirect` is a container class used to generate redirect responses and their respective OpenAPI documentation.
See the [API Reference][starlite.datastructures.Redirect] for full details on the `Redirect` class and the kwargs it accepts.
