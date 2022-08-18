# CSRF

CSRF ([Cross-site request forgery](https://en.wikipedia.org/wiki/Cross-site_request_forgery)) is a type of attack
where unauthorized commands are submitted from a user that the web application trusts. This attack often uses
social engineering that tricks the victim into clicking a URL that contains a maliciously crafted, unauthorized
request for a particular Web application. The user’s browser then sends this maliciously crafted request to the
targeted Web application. If the user is in an active session with the Web application, the application treats
this new request as an authorized request submitted by the user. Thus, the attacker can force the user to perform
an action the user didn't intend, for example:

```text
POST /send-money HTTP/1.1
Host: target.web.app
Content-Type: application/x-www-form-urlencoded

amount=1000usd&to=attacker@evil.com
```

This middleware prevents CSRF attacks by doing the following:

1. On the first "safe" request (e.g `GET`) - set a cookie with a special token created by the server
2. On each subsequent "unsafe" request (e.g `POST`) - make sure the request contains an additional header that has
   this token

To enable CSRF protection in a Starlite application simply pass an instance of `starlite.config.CSRFConfig`
to the Starlite constructor:

```python
from starlite import Starlite
from starlite.config import CSRFConfig

csrf_config = CSRFConfig(secret="my-secret")

app = Starlite(route_handlers=[...], csrf_config=csrf_config)
```

You can pass the following kwargs to `CSRFConfig`:

- `secret` - this is the only mandatory parameter, it's a string that is used to create an HMAC to sign the CSRF token
- `cookie_name` - the CSRF cookie name, set to `csrftoken` by default
- `cookie_path` - the CSRF cookie path, set to `/` by default
- `header_name` - the header that will be expected in each request, has a default value of `x-csrftoken`
- `cookie_secure` - a boolean value indicating whether to set the `Secure` attribute on the cookie, set to `False`
  by default
- `cookie_httponly` - a boolean value indicating whether to set the `HttpOnly` attribute on the cookie, set to `False`
  by default
- `cookie_samesite` - the value that will be set in the `SameSite` attribute of the cookie. Can have one of the
  values `lax`, `secure`, `none`. Has a default of `lax`
- `cookie_domain` - specifies which hosts can receive the cookie. Has a default value of `None` which means it
  defaults to the same host that set the cookie
- `safe_methods` - a set of "safe methods" that can set the cookie. The default values are `GET` and `HEAD`
