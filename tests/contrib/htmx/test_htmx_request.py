from starlite import MediaType, Response, get
from starlite.contrib.htmx._utils import HTMXHeaders
from starlite.contrib.htmx.request import HTMXRequest
from starlite.status_codes import HTTP_200_OK
from starlite.testing import create_test_client


def test_health_check() -> None:
    @get("/health-check", media_type=MediaType.TEXT)
    def health_check() -> str:
        return "healthy"

    with create_test_client(route_handlers=health_check) as client:
        response = client.get("/health-check")
        assert response.status_code == HTTP_200_OK
        assert response.text == "healthy"


async def test_bool_default() -> None:
    @get("/", media_type=MediaType.TEXT)
    def handler(request: HTMXRequest) -> Response:
        return Response(content=bool(request.htmx))

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get("/")
        assert response.text == "false"


async def test_bool_false() -> None:
    @get("/", media_type=MediaType.TEXT)
    def handler(request: HTMXRequest) -> Response:
        return Response(content=bool(request.htmx))

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get("/", headers={HTMXHeaders.REQUEST.value: "false"})
        assert response.text == "false"


async def test_bool_true() -> None:
    @get("/", media_type=MediaType.TEXT)
    def handler(request: HTMXRequest) -> Response:
        return Response(content=bool(request.htmx))

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get("/", headers={HTMXHeaders.REQUEST.value: "true"})
        assert response.text == "true"


async def test_boosted_default() -> None:
    @get("/", media_type=MediaType.TEXT)
    def handler(request: HTMXRequest) -> Response:
        return Response(content=request.htmx.boosted)

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get("/")
        assert response.text == "false"


async def test_boosted_set() -> None:
    @get("/", media_type=MediaType.TEXT)
    def handler(request: HTMXRequest) -> Response:
        return Response(content=request.htmx.boosted)

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get("/", headers={HTMXHeaders.BOOSTED.value: "true"})
        assert response.text == "true"


def test_current_url_default() -> None:
    @get("/", media_type=MediaType.TEXT)
    def handler(request: HTMXRequest) -> Response:
        assert request.htmx.current_url is None
        return Response(content=request.htmx.current_url)

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get("/")
        assert response.text == "null"


def test_current_url_set() -> None:
    @get("/", media_type=MediaType.TEXT)
    def handler(request: HTMXRequest) -> Response:
        assert request.htmx.current_url == "https://example.com"
        return Response(content=request.htmx.current_url)

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get("/", headers={HTMXHeaders.CURRENT_URL.value: "https://example.com"})
        assert response.text == '"https://example.com"'


def test_current_url_set_url_encoded() -> None:
    @get("/", media_type=MediaType.TEXT)
    def handler(request: HTMXRequest) -> Response:
        assert request.htmx.current_url == "https://example.com/?"
        return Response(content=request.htmx.current_url)

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get(
            "/",
            headers={
                HTMXHeaders.CURRENT_URL.value: "https%3A%2F%2Fexample.com%2F%3F",
                HTMXHeaders.CURRENT_URL.value + "-URI-AutoEncoded": "true",
            },
        )
        assert response.text == '"https://example.com/?"'


def test_current_url_abs_path_default() -> None:
    @get("/", media_type=MediaType.TEXT)
    def handler(request: HTMXRequest) -> Response:
        assert request.htmx.current_url_abs_path is None
        return Response(content=request.htmx.current_url_abs_path)

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get("/")
        assert response.text == "null"


def test_current_url_abs_path_set() -> None:
    @get("/", media_type=MediaType.TEXT)
    def handler(request: HTMXRequest) -> Response:
        assert request.htmx.current_url_abs_path == "/duck/?quack=true#h2"
        return Response(content=request.htmx.current_url_abs_path)

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get(
            "/", headers={HTMXHeaders.CURRENT_URL.value: "http://testserver.local/duck/?quack=true#h2"}
        )
        assert response.text == '"/duck/?quack=true#h2"'


def test_current_url_abs_path_set_other_domain() -> None:
    @get("/", media_type=MediaType.TEXT)
    def handler(request: HTMXRequest) -> Response:
        assert request.htmx.current_url_abs_path is None
        return Response(content=request.htmx.current_url_abs_path)

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get("/", headers={HTMXHeaders.CURRENT_URL.value: "http://example.com/duck/?quack=true#h2"})
        assert response.text == "null"


def test_history_restore_request_false() -> None:
    @get("/", media_type=MediaType.TEXT)
    def handler(request: HTMXRequest) -> Response:
        assert request.htmx.history_restore_request is False
        return Response(content=request.htmx.history_restore_request)

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get("/", headers={HTMXHeaders.HISTORY_RESTORE_REQUEST.value: "false"})
        assert response.text == "false"


def test_history_restore_request_true() -> None:
    @get("/", media_type=MediaType.TEXT)
    def handler(request: HTMXRequest) -> Response:
        assert request.htmx.history_restore_request is True
        return Response(content=request.htmx.history_restore_request)

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get("/", headers={HTMXHeaders.HISTORY_RESTORE_REQUEST.value: "true"})
        assert response.text == "true"


def test_prompt_default() -> None:
    @get("/", media_type=MediaType.TEXT)
    def handler(request: HTMXRequest) -> Response:
        assert request.htmx.prompt is None
        return Response(content=request.htmx.prompt)

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get("/")
        assert response.text == "null"


def test_prompt_set() -> None:
    @get("/", media_type=MediaType.TEXT)
    def handler(request: HTMXRequest) -> Response:
        assert request.htmx.prompt == "Yes"
        return Response(content=request.htmx.prompt)

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get("/", headers={HTMXHeaders.PROMPT.value: "Yes"})
        assert response.text == '"Yes"'


def test_target_default() -> None:
    @get("/", media_type=MediaType.TEXT)
    def handler(request: HTMXRequest) -> Response:
        assert request.htmx.target is None
        return Response(content=request.htmx.target)

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get("/")
        assert response.text == "null"


def test_target_set() -> None:
    @get("/", media_type=MediaType.TEXT)
    def handler(request: HTMXRequest) -> Response:
        assert request.htmx.target == "#element"
        return Response(content=request.htmx.target)

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get("/", headers={HTMXHeaders.TARGET.value: "#element"})
        assert response.text == '"#element"'


def test_trigger_default() -> None:
    @get("/", media_type=MediaType.TEXT)
    def handler(request: HTMXRequest) -> Response:
        assert request.htmx.trigger is None
        return Response(content=request.htmx.trigger)

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get("/")
        assert response.text == "null"


def test_trigger_set() -> None:
    @get("/", media_type=MediaType.TEXT)
    def handler(request: HTMXRequest) -> Response:
        assert request.htmx.trigger == "#element"
        return Response(content=request.htmx.trigger)

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get("/", headers={HTMXHeaders.TRIGGER_ID.value: "#element"})
        assert response.text == '"#element"'


def test_trigger_name_default() -> None:
    @get("/", media_type=MediaType.TEXT)
    def handler(request: HTMXRequest) -> Response:
        assert request.htmx.trigger_name is None
        return Response(content=request.htmx.trigger_name)

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get("/")
        assert response.text == "null"


def test_trigger_name_set() -> None:
    @get("/", media_type=MediaType.TEXT)
    def handler(request: HTMXRequest) -> Response:
        assert request.htmx.trigger_name == "name_of_element"
        return Response(content=request.htmx.trigger_name)

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get("/", headers={HTMXHeaders.TRIGGER_NAME.value: "name_of_element"})
        assert response.text == '"name_of_element"'


def test_triggering_event_none() -> None:
    @get("/", media_type=MediaType.TEXT)
    def handler(request: HTMXRequest) -> Response:
        assert request.htmx.triggering_event is None
        return Response(content=request.htmx.triggering_event)

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get("/")
        assert response.text == "null"


def test_triggering_event_bad_json() -> None:
    @get("/", media_type=MediaType.TEXT)
    def handler(request: HTMXRequest) -> Response:
        assert request.htmx.triggering_event is None
        return Response(content=request.htmx.triggering_event)

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get("/", headers={HTMXHeaders.TRIGGERING_EVENT.value: "{"})
        assert response.text == "null"


def test_triggering_event_good_json() -> None:
    @get("/", media_type=MediaType.TEXT)
    def handler(request: HTMXRequest) -> Response:
        assert request.htmx.triggering_event == {"target": None}
        return Response(content=request.htmx.triggering_event)

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get(
            "/",
            headers={
                HTMXHeaders.TRIGGERING_EVENT.value: "%7B%22target%22%3A%20null%7D",
                HTMXHeaders.TRIGGERING_EVENT.value + "-uri-autoencoded": "true",
            },
        )
        assert response.text == '{"target":null}'
