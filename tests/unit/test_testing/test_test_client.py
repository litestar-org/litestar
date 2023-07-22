from typing import TYPE_CHECKING, Any, Dict

import pytest

from litestar import Litestar, Request, get, post
from litestar.stores.base import Store
from litestar.testing import TestClient

if TYPE_CHECKING:
    from litestar.middleware.session.base import BaseBackendConfig
    from litestar.types import AnyIOBackend


@pytest.mark.parametrize("with_domain", [False, True])
def test_test_client_set_session_data(
    with_domain: bool,
    session_backend_config: "BaseBackendConfig",
    test_client_backend: "AnyIOBackend",
) -> None:
    session_data = {"foo": "bar"}

    if with_domain:
        session_backend_config.domain = "testserver.local"

    @get(path="/test")
    def get_session_data(request: Request) -> Dict[str, Any]:
        return request.session

    app = Litestar(route_handlers=[get_session_data], middleware=[session_backend_config.middleware])

    with TestClient(app=app, session_config=session_backend_config, backend=test_client_backend) as client:
        client.set_session_data(session_data)
        assert session_data == client.get("/test").json()


@pytest.mark.parametrize("with_domain", [False, True])
def test_test_client_get_session_data(
    with_domain: bool, session_backend_config: "BaseBackendConfig", test_client_backend: "AnyIOBackend", store: Store
) -> None:
    session_data = {"foo": "bar"}

    if with_domain:
        session_backend_config.domain = "testserver.local"

    @post(path="/test")
    def set_session_data(request: Request) -> None:
        request.session.update(session_data)

    app = Litestar(
        route_handlers=[set_session_data], middleware=[session_backend_config.middleware], stores={"session": store}
    )

    with TestClient(app=app, session_config=session_backend_config, backend=test_client_backend) as client:
        client.post("/test")
        assert client.get_session_data() == session_data


def test_create_test_client_warns_problematic_domain() -> None:
    with pytest.warns(UserWarning):
        TestClient(app=Litestar(), base_url="http://testserver")
