from litestar.middleware.authentication import AbstractAuthenticationMiddleware
from litestar.middleware.base import ASGIMiddleware
from litestar.middleware.constraints import MiddlewareConstraints


class CachingMiddleware(ASGIMiddleware):
    constraints = MiddlewareConstraints(after=(AbstractAuthenticationMiddleware,))
