from os import urandom

from starlite import Starlite
from starlite.middleware.session.cookie_backend import CookieBackendConfig

session_config = CookieBackendConfig(secret=urandom(16))  # type: ignore[arg-type]

app = Starlite(middleware=[session_config.middleware])
