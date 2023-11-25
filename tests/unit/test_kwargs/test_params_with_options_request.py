from litestar import Router, get
from litestar.app import Litestar
from litestar.config.cors import CORSConfig
from litestar.params import Parameter
from litestar.status_codes import HTTP_204_NO_CONTENT
from litestar.testing import create_test_client


@get(path="/test")
def a_handler(tenant: str) -> None:
    assert tenant


router = Router(
    "/",
    route_handlers=[a_handler],
    parameters={
        "tenant": Parameter(str, header="TENANT", required=True),
    },
)

app = Litestar(
    route_handlers=[router],
    openapi_config=None,
    cors_config=CORSConfig(),
)


def test_header_params_with_options_request() -> None:
    with create_test_client(app) as client:
        response = client.options(
            "/test",
            headers={},
        )
        assert response.status_code == HTTP_204_NO_CONTENT
