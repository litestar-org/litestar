# Allowed Hosts

Another common security mechanism is to require that each incoming request has a "HOST" header, and then to restrict
hosts to a specific set of domains - what's called "allowed hosts". To enable this middleware simply pass a list of
trusted hosts to the Starlite constructor:

```python
from starlite import Starlite

app = Starlite(
    request_handlers=[...], allowed_hosts=["*.example.com", "www.wikipedia.org"]
)
```

You can use `*` to match any subdomains, as in the above.
