from os import urandom

from litestar import Litestar
from litestar.middleware.session import SessionMiddleware
from litestar.middleware.session.client_side import ClientSideSessionBackend, CookieBackendConfig

session_config = CookieBackendConfig(secret=urandom(16))  # type: ignore

app = Litestar(middleware=[SessionMiddleware(ClientSideSessionBackend(session_config))])
