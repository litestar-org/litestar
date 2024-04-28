from typing import Any

from litestar import get


@get("/secured")
def secured_route() -> Any: ...


@get("/unsecured", exclude_from_auth=True)
def unsecured_route() -> Any: ...
