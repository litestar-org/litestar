import json
import os
from typing import Any, Callable, Dict, Union

import pytest
from pydantic import BaseModel, SecretBytes

from starlite import HttpMethod, Request, RequestEncodingType, Starlite, State, get
from starlite.datastructures import Cookie
from starlite.enums import ParamType
from starlite.middleware.session import SessionCookieConfig
from starlite.testing import RequestFactory, TestClient
from tests import Pet, PetFactory

_DEFAULT_REQUEST_FACTORY_URL = "http://test.org:3000/"

pet = PetFactory.build()


def test_request_factory_no_cookie_header() -> None:
    headers: Dict[str, str] = dict()
    RequestFactory._create_cookie_header(headers, None)
    assert headers == {}


def test_request_factory_str_cookie_header() -> None:
    headers: Dict[str, str] = dict()
    cookie_as_str = "test=cookie; starlite=cookie"
    RequestFactory._create_cookie_header(headers, cookie_as_str)
    assert headers[ParamType.COOKIE] == cookie_as_str


def test_request_factory_cookie_list_header() -> None:
    headers: Dict[str, str] = dict()
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

    for (key, value) in built_headers:
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
            lambda data: data == "&".join([f"{key}={value}" for key, value in pet.dict(exclude_none=True).items()]),
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
    request = RequestFactory().get("/")
    assert isinstance(request.app, Starlite)
    assert request.url == request.base_url == _DEFAULT_REQUEST_FACTORY_URL
    assert request.method == HttpMethod.GET
    assert request.query_params == {}


def test_request_factory_create_with_params() -> None:
    class User(BaseModel):
        pass

    class Auth(BaseModel):
        pass

    app = Starlite(route_handlers=[])
    server = "starlite.org"
    port = 5000
    root_path = "/root"
    path = "/path"
    user = User()
    auth = Auth()
    scheme = "https"
    session = {"param1": "a", "param2": 2}
    request = RequestFactory(app, server, port, root_path, scheme).get(path, session=session, user=user, auth=auth)
    assert request.app == app
    assert request.base_url == f"{scheme}://{server}:{port}{root_path}/"
    assert request.url == f"{scheme}://{server}:{port}{root_path}{path}"
    assert request.method == HttpMethod.GET
    assert request.query_params == {}
    assert request.user == user
    assert request.auth == auth
    assert request.session == session


def test_request_factory_get() -> None:
    query_params = {"p1": "a", "p2": 2, "p3": ["c", "d"]}
    headers = {"header1": "value1"}
    request = RequestFactory().get("/", headers=headers, query_params=query_params)  # type: ignore[arg-type]
    assert request.method == HttpMethod.GET
    assert request.url == f"{_DEFAULT_REQUEST_FACTORY_URL}?p1=a&p2=2&p3=c&p3=d"
    assert len(request.headers.keys()) == 1
    assert request.headers.get("header1") == "value1"


def test_request_factory_delete() -> None:
    headers = {"header1": "value1"}
    request = RequestFactory().delete("/", headers=headers)
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


@pytest.mark.parametrize("enable_session, session_data", [(True, {"user": "test-user"}), (False, {})])
def test_test_client(enable_session: bool, session_data: Dict[str, str]) -> None:
    def start_up_handler(state: State) -> None:
        state.value = 1

    @get(path="/test")
    def test_handler(state: State, request: Request) -> None:
        assert state.value == 1
        assert request.session == session_data

    session_config = SessionCookieConfig(secret=SecretBytes(os.urandom(16)))
    app = Starlite(route_handlers=[test_handler], on_startup=[start_up_handler], middleware=[session_config.middleware])

    with TestClient(app=app, session_config=session_config if enable_session else None) as client:
        cookies = client.create_session_cookies(session_data=session_data)
        client.get("/test", cookies=cookies)
        assert app.state.value == 1
