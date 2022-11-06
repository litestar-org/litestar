# Allowed Hosts

Another common security mechanism is to require that each incoming request has a "Host" or "X-Fowarded-Host" header,
and then to restrict hosts to a specific set of domains - what's called "allowed hosts".

Starlite includes an `AllowedHostsMiddleware` class that can be easily enabled by either passing an instance of
[AllowedHostsConfig][starlite.config.AllowedHostsConfig] or a list of domains to
the [Starlite constructor][starlite.app.Starlite]:

```python
from starlite import Starlite, AllowedHostsConfig

app = Starlite(
    route_handlers=[...],
    allowed_hosts=AllowedHostsConfig(
        allowed_hosts=["*.example.com", "www.wikipedia.org"]
    ),
)
```

!!! note
    You can use wildcard prefixes (`*.`) in the beginning of a domain to match any combination of subdomains. Thus,
    `*.example.com` will match `www.example.com` but also `x.y.z.example.com` etc. You can also simply put `*` in trusted
    hosts, which means - allow all. This though is basically turning the middleware off, so its better to simply not enable
    it to begin with in this case. You should note that a wildcard cannot be used only in the prefix of a domain name,
    not in the middle or end. Doing so will result in a validation exception being raised.

For further configuration options, consult the [config reference documentation][starlite.config.AllowedHostsConfig].
