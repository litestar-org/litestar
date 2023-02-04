from typing import TYPE_CHECKING

import pytest

from starlite import Starlite, asgi
from starlite.exceptions import ImproperlyConfiguredException

if TYPE_CHECKING:
    from starlite.types import Receive, Scope, Send


def test_add_mount_route_disallow_path_parameter() -> None:
    async def handler(scope: "Scope", receive: "Receive", send: "Send") -> None:
        return None

    with pytest.raises(ImproperlyConfiguredException):
        Starlite(route_handlers=[asgi("/mount-path", is_static=True)(handler), asgi("/mount-path/{id:str}")(handler)])
