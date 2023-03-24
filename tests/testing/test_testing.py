import json
from typing import TYPE_CHECKING, Any, Callable, Dict, Union

import pytest
from pydantic import BaseModel

from starlite import HttpMethod, Request, Starlite, get, post
from starlite.datastructures import Cookie, MultiDict
from starlite.enums import ParamType, RequestEncodingType
from starlite.middleware.session.server_side import ServerSideSessionConfig
from starlite.stores.base import Store
from starlite.stores.redis import RedisStore
from starlite.testing import RequestFactory, TestClient, create_test_client
from tests import Pet, PetFactory

if TYPE_CHECKING:
    from starlite.middleware.session.base import BaseBackendConfig
    from starlite.types import AnyIOBackend

_DEFAULT_REQUEST_FACTORY_URL = "http://test.org:3000/"

pet = PetFactory.build()


def test_request_factory_no_cookie_header() -> None:
    headers: Dict[str, str] = {}
    RequestFactory._create_cookie_header(headers)
    assert headers == {}


def test_request_factory_str_cookie_header() -> None:
    headers: Dict[str, str] = {}
    cookie_as_str = "test=cookie; starlite=cookie"
    RequestFactory._create_cookie_header(headers, cookie_as_str)
    assert headers[ParamType.COOKIE] == cookie_as_str


def test_request_factory_cookie_list_header() -> None:
    headers: Dict[str, str] = {}
    cookie_list = [Cookie(key="test", value="cookie"), Cookie(key="starlite", value="cookie", path="/test")]
    RequestFactory._create_cookie_header(headers, cookie_list)
    assert headers[ParamType.COOKIE] == "test=cookie; Path=/; SameSite=lax; starlite=cookie; Path=/test; SameSite=lax"


def test_request_factory_build_headers() -> None:
    headers = {
        "header1": "value1",
        "header2": "value2",
    }
    built_headers = RequestFactory()._build_headers(headers)

    assert len(built_headers) == len(headers.keys())

    for key, value in built_headers:
        decoded_key = key.decode("latin1")
        decoded_value = value.decode("latin1")
        assert decoded_key in headers
        assert headers[decoded_key] == decoded_value


@pytest.mark.parametrize("data", [pet, pet.dict()])
async def test_request_factory_create_with_data(data: Union[Pet, Dict[str, Any]]) -> None:
    request = RequestFactory()._create_request_with_data(
        HttpMethod.POST,
        "/",
        data=data,
    )
    body = await request.body()
    assert json.loads(body.decode()) == pet.dict()


@pytest.mark.parametrize(
    "request_media_type, verify_data",
    [
        [RequestEncodingType.JSON, lambda data: json.loads(data) == pet.dict()],
        [RequestEncodingType.MULTI_PART, lambda data: "Content-Disposition" in data],
        [
            RequestEncodingType.URL_ENCODED,
            lambda data: data == f"name={pet.name}&species={pet.species.value}&age={pet.age}",
        ],
    ],
)
async def test_request_factory_create_with_content_type(
    request_media_type: RequestEncodingType, verify_data: Callable[[str], bool]
) -> None:
    request = RequestFactory()._create_request_with_data(
        HttpMethod.POST,
        "/",
        data=pet.dict(),
        request_media_type=request_media_type,
    )
    assert request.headers["Content-Type"].startswith(request_media_type.value)
    body = await request.body()
    assert verify_data(body.decode("utf-8"))


def test_request_factory_create_with_default_params() -> None:
    request = RequestFactory().get()
    assert isinstance(request.app, Starlite)
    assert request.url == request.base_url == _DEFAULT_REQUEST_FACTORY_URL
    assert request.method == HttpMethod.GET
    assert not request.query_params
    assert not request.state
    assert not request.path_params
    assert request.route_handler
    assert request.scope["http_version"] == "1.1"
    assert request.scope["raw_path"] == b"/"


def test_request_factory_create_with_params() -> None:
    class User(BaseModel):
        pass

    class Auth(BaseModel):
        pass

    @get("/path")
    def handler() -> None:
        ...

    app = Starlite(route_handlers=[])
    server = "starlite.org"
    port = 5000
    root_path = "/root"
    path = "/path"
    user = User()
    auth = Auth()
    scheme = "https"
    session = {"param1": "a", "param2": 2}
    state = {"weather": "sunny"}
    path_params = {"param": "a"}
    request = RequestFactory(app, server, port, root_path, scheme).get(
        path,
        session=session,
        user=user,
        auth=auth,
        state=state,
        path_params=path_params,
        http_version="2.0",
        route_handler=handler,
    )

    assert request.app == app
    assert request.base_url == f"{scheme}://{server}:{port}{root_path}/"
    assert request.url == f"{scheme}://{server}:{port}{root_path}{path}"
    assert request.method == HttpMethod.GET
    assert request.query_params == MultiDict()
    assert request.user == user
    assert request.auth == auth
    assert request.session == session
    assert request.state.weather == "sunny"
    assert request.path_params == path_params
    assert request.route_handler == handler
    assert request.scope["http_version"] == "2.0"
    assert request.scope["raw_path"] == path.encode("ascii")


def test_request_factory_get() -> None:
    query_params = {"p1": "a", "p2": 2, "p3": ["c", "d"]}
    headers = {"header1": "value1"}
    request = RequestFactory().get(headers=headers, query_params=query_params)  # type: ignore[arg-type]
    assert request.method == HttpMethod.GET
    assert request.url == f"{_DEFAULT_REQUEST_FACTORY_URL}?p1=a&p2=2&p3=c&p3=d"
    assert len(request.headers.keys()) == 1
    assert request.headers.get("header1") == "value1"


def test_request_factory_delete() -> None:
    headers = {"header1": "value1"}
    request = RequestFactory().delete(headers=headers)
    assert request.method == HttpMethod.DELETE
    assert request.url == _DEFAULT_REQUEST_FACTORY_URL
    assert len(request.headers.keys()) == 1
    assert request.headers.get("header1") == "value1"


@pytest.mark.parametrize(
    "factory, method",
    [
        (RequestFactory().post, HttpMethod.POST),
        (RequestFactory().put, HttpMethod.PUT),
        (RequestFactory().patch, HttpMethod.PATCH),
    ],
)
async def test_request_factory_post_put_patch(factory: Callable, method: HttpMethod) -> None:
    headers = {"header1": "value1"}
    request = factory("/", headers=headers, data=pet)
    assert request.method == method
    # Headers should include "header1" and "Content-Type"
    assert len(request.headers.keys()) == 3
    assert request.headers.get("header1") == "value1"
    body = await request.body()
    assert json.loads(body) == pet.dict()


@pytest.fixture()
def skip_for_trio_redis(
    session_backend_config: "BaseBackendConfig", test_client_backend: "AnyIOBackend", store: Store
) -> None:
    if (
        isinstance(session_backend_config, ServerSideSessionConfig)
        and isinstance(store, RedisStore)
        and test_client_backend == "trio"
    ):
        pytest.skip("fakeredis does not always play well with trio, so skip this for now")


@pytest.mark.usefixtures("skip_for_trio_redis")
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

    app = Starlite(route_handlers=[get_session_data], middleware=[session_backend_config.middleware])

    with TestClient(app=app, session_config=session_backend_config, backend=test_client_backend) as client:
        client.set_session_data(session_data)
        assert session_data == client.get("/test").json()


@pytest.mark.usefixtures("skip_for_trio_redis")
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

    app = Starlite(
        route_handlers=[set_session_data], middleware=[session_backend_config.middleware], stores={"session": store}
    )

    with TestClient(app=app, session_config=session_backend_config, backend=test_client_backend) as client:
        client.post("/test")
        assert client.get_session_data() == session_data


def test_create_test_client_warns_problematic_domain() -> None:
    with pytest.warns(UserWarning):
        create_test_client(base_url="http://testserver", route_handlers=[])
