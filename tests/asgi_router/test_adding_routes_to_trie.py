from typing import TYPE_CHECKING

import pytest

from litestar import Litestar, asgi
from litestar.exceptions import ImproperlyConfiguredException

if TYPE_CHECKING:
    from litestar.types import Receive, Scope, Send


def test_add_mount_route_disallow_path_parameter() -> None:
    async def handler(scope: "Scope", receive: "Receive", send: "Send") -> None:
        return None

    with pytest.raises(ImproperlyConfiguredException):
        Litestar(route_handlers=[asgi("/mount-path", is_static=True)(handler), asgi("/mount-path/{id:str}")(handler)])
