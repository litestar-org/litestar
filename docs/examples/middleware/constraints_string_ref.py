from litestar.middleware.base import ASGIMiddleware
from litestar.middleware.constraints import MiddlewareConstraints


class SomeMiddleware(ASGIMiddleware):
    constraints = MiddlewareConstraints().apply_after(
        "some_package.some_module.SomeMiddleware",
        ignore_import_error=True,
    )
