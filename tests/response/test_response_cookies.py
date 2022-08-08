from starlite import Controller, Cookie, HttpMethod, Router, Starlite, get
from starlite.testing import create_test_client


def test_response_cookies() -> None:
    router_first = Cookie(key="second", value="1")
    router_second = Cookie(key="third", value="2")
    controller_first = Cookie(key="first", value="3")
    controller_second = Cookie(key="second", value="4")
    app_first = Cookie(key="first", value="5")
    app_second = Cookie(key="fourth", value="6")
    local_first = Cookie(key="first", value="7")

    test_path = "/test"

    class MyController(Controller):
        path = test_path
        response_cookies = [controller_first, controller_second]

        @get(
            path="/{path_param:str}",
            response_cookies=[local_first],
        )
        def test_method(self) -> None:
            pass

    first_router = Router(path="/users", response_cookies=[router_first, router_second], route_handlers=[MyController])

    second_router = Router(path="/external", response_cookies=[Cookie(key="external", value="nope")], route_handlers=[])

    app = Starlite(
        openapi_config=None,
        response_cookies=[app_first, app_second],
        route_handlers=[first_router, second_router],
    )
    route_handler, _ = app.routes[0].route_handler_map[HttpMethod.GET]  # type: ignore
    response_cookies = {cookie.key: cookie.value for cookie in route_handler.resolve_response_cookies()}
    assert response_cookies["first"] == local_first.value
    assert response_cookies["second"] == controller_second.value
    assert response_cookies["third"] == router_second.value
    assert response_cookies["fourth"] == app_second.value
    assert "external" not in response_cookies


def test_response_cookie_rendering() -> None:
    @get(
        "/",
        response_cookies=[Cookie(key="test", value="123")],
    )
    def test_method() -> None:
        return None

    with create_test_client(test_method) as client:
        response = client.get("/")
        assert response.headers["Set-Cookie"] == "test=123; Path=/; SameSite=lax"
