from pathlib import Path
from typing import Any

import pytest

from starlite import MediaType, TemplateConfig, create_test_client, get
from starlite.contrib.htmx.request import HTMXRequest
from starlite.contrib.htmx.response import (
    ClientRedirect,
    ClientRefresh,
    HTMXTemplate,
    HXLocation,
    HXStopPolling,
    PushUrl,
    Reswap,
    Retarget,
    TriggerEvent,
)
from starlite.contrib.htmx.utils import HX
from starlite.contrib.jinja import JinjaTemplateEngine
from starlite.contrib.mako import MakoTemplateEngine
from starlite.status_codes import HTTP_200_OK


async def test_hx_stop_polling_response() -> None:
    @get("/")
    def handler() -> HXStopPolling:
        return HXStopPolling()

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get("/")
        assert response.status_code == 286


async def test_client_redirect_response() -> None:
    @get("/")
    def handler() -> ClientRedirect:
        return ClientRedirect(redirect_to="https://example.com")

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.headers.get(HX.REDIRECT) == "https://example.com"
        assert response.headers.get("location") is None


async def test_client_refresh_response() -> None:
    @get("/")
    def handler() -> ClientRefresh:
        return ClientRefresh()

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.headers[HX.REFRESH] == "true"


async def test_push_url_false_response() -> None:
    @get("/", media_type=MediaType.TEXT)
    def handler() -> PushUrl:
        return PushUrl(content="Success!")

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.text == '"Success!"'
        assert response.headers[HX.PUSH_URL] == "false"


async def test_push_url_response() -> None:
    @get("/", media_type=MediaType.TEXT)
    def handler() -> PushUrl:
        return PushUrl(content="Success!", push="/index.html")

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.text == '"Success!"'
        assert response.headers[HX.PUSH_URL] == "/index.html"


async def test_reswap_response() -> None:
    @get("/")
    def handler() -> Reswap:
        return Reswap(content="Success!", method="beforebegin")

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.text == '"Success!"'
        assert response.headers[HX.RE_SWAP] == "beforebegin"


async def test_retarget_response() -> None:
    @get("/")
    def handler() -> Retarget:
        return Retarget(content="Success!", target="#element")

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.text == '"Success!"'
        assert response.headers[HX.RE_TARGET] == "#element"


async def test_trigger_event_response_success() -> None:
    @get("/")
    def handler() -> TriggerEvent:
        return TriggerEvent(
            content="Success!", name="alert", after="receive", params={"warning": "Confirm your choice!"}
        )

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.text == '"Success!"'
        assert response.headers[HX.TRIGGER_EVENT] == '{"alert":{"warning":"Confirm your choice!"}}'


async def test_trigger_event_response_no_params() -> None:
    @get("/")
    def handler() -> TriggerEvent:
        return TriggerEvent(content="Success!", name="alert", after="receive")

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.text == '"Success!"'
        assert response.headers[HX.TRIGGER_EVENT] == '{"alert":{}}'


async def test_trigger_event_response_after_settle() -> None:
    @get("/")
    def handler() -> TriggerEvent:
        return TriggerEvent(
            content="Success!", name="alert", after="settle", params={"warning": "Confirm your choice!"}
        )

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.text == '"Success!"'
        assert response.headers[HX.TRIGGER_AFTER_SETTLE] == '{"alert":{"warning":"Confirm your choice!"}}'


async def test_trigger_event_response_after_swap() -> None:
    @get("/")
    def handler() -> TriggerEvent:
        return TriggerEvent(content="Success!", name="alert", after="swap", params={"warning": "Confirm your choice!"})

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.text == '"Success!"'
        assert response.headers[HX.TRIGGER_AFTER_SWAP] == '{"alert":{"warning":"Confirm your choice!"}}'


async def test_trigger_event_response_invalid_after() -> None:
    @get("/")
    def handler() -> TriggerEvent:
        return TriggerEvent(
            content="Success!", name="alert", after="invalid", params={"warning": "Confirm your choice!"}  # type: ignore
        )

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get("/")
        detail = response.json()
        assert detail["status_code"] == 500
        assert (
            detail["detail"]
            == "ValueError(\"Invalid value for after param. Value must be either 'receive', 'settle' or 'swap'.\")"
        )


async def test_hx_location_response_success() -> None:
    @get("/")
    def handler() -> HXLocation:
        return HXLocation(redirect_to="/contact-us")

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get("/")
        spec = response.headers[HX.LOCATION]
        assert response.status_code == HTTP_200_OK
        assert "Location" not in response.headers
        assert spec == '{"path":"/contact-us"}'


async def test_hx_location_response_with_all_parameters() -> None:
    @get("/")
    def handler() -> HXLocation:
        return HXLocation(
            redirect_to="/contact-us",
            source="#button",
            event="click",
            target="#content",
            swap="innerHTML",
            headers={"attribute": "value"},
            values={"action": "true"},
        )

    with create_test_client(route_handlers=[handler], request_class=HTMXRequest) as client:
        response = client.get("/")
        spec = response.headers[HX.LOCATION]
        assert response.status_code == HTTP_200_OK
        assert "Location" not in response.headers
        assert (
            spec
            == '{"path":"/contact-us","source":"#button","event":"click","target":"#content","swap":"innerHTML","headers":{"attribute":"value"},"values":{"action":"true"}}'
        )


@pytest.mark.parametrize(
    "engine, template, expected",
    (
        (JinjaTemplateEngine, "path: {{ request.scope['path'] }}", "path: /"),
        (MakoTemplateEngine, "path: ${request.scope['path']}", "path: /"),
    ),
)
def test_HTMXTemplate_response_success(engine: Any, template: str, expected: str, template_dir: Path) -> None:
    Path(template_dir / "abc.html").write_text(template)

    @get(path="/", media_type=MediaType.HTML)
    def handler() -> HTMXTemplate:
        return HTMXTemplate(
            name="abc.html",
            context={"request": {"scope": {"path": "nope"}}},
            push="/about",
            re_swap="beforebegin",
            re_target="#new-target-id",
            trigger_event="showMessage",
            params={"alert": "Confirm your Choice."},
            after="receive",
        )

    with create_test_client(
        route_handlers=[handler],
        template_config=TemplateConfig(
            directory=template_dir,
            engine=engine,
        ),
    ) as client:
        response = client.get("/")
        assert response.text == expected
        assert response.headers.get(HX.PUSH_URL) == "/about"
        assert response.headers.get(HX.RE_SWAP) == "beforebegin"
        assert response.headers.get(HX.RE_TARGET) == "#new-target-id"
        assert response.headers.get(HX.TRIGGER_EVENT) == '{"showMessage":{"alert":"Confirm your Choice."}}'


@pytest.mark.parametrize(
    "engine, template, expected",
    (
        (JinjaTemplateEngine, "path: {{ request.scope['path'] }}", "path: /"),
        (MakoTemplateEngine, "path: ${request.scope['path']}", "path: /"),
    ),
)
def test_HTMXTemplate_response_no_params(engine: Any, template: str, expected: str, template_dir: Path) -> None:
    Path(template_dir / "abc.html").write_text(template)

    @get(path="/", media_type=MediaType.HTML)
    def handler() -> HTMXTemplate:
        return HTMXTemplate(
            name="abc.html",
            context={"request": {"scope": {"path": "nope"}}},
        )

    with create_test_client(
        route_handlers=[handler],
        template_config=TemplateConfig(
            directory=template_dir,
            engine=engine,
        ),
    ) as client:
        response = client.get("/")
        assert response.text == expected
        assert response.headers.get(HX.PUSH_URL) is None
        assert response.headers.get(HX.RE_SWAP) is None
        assert response.headers.get(HX.RE_TARGET) is None
        assert response.headers.get(HX.TRIGGER_EVENT) is None


@pytest.mark.parametrize(
    "engine, template, expected",
    (
        (JinjaTemplateEngine, "path: {{ request.scope['path'] }}", "path: /"),
        (MakoTemplateEngine, "path: ${request.scope['path']}", "path: /"),
    ),
)
def test_HTMXTemplate_response_push_url_set_to_false(
    engine: Any, template: str, expected: str, template_dir: Path
) -> None:
    Path(template_dir / "abc.html").write_text(template)

    @get(path="/", media_type=MediaType.HTML)
    def handler() -> HTMXTemplate:
        return HTMXTemplate(
            name="abc.html",
            context={"request": {"scope": {"path": "nope"}}},
            push=False,
        )

    with create_test_client(
        route_handlers=[handler],
        template_config=TemplateConfig(
            directory=template_dir,
            engine=engine,
        ),
    ) as client:
        response = client.get("/")
        assert response.text == expected
        assert response.headers.get(HX.PUSH_URL) == "false"
        assert response.headers.get(HX.RE_SWAP) is None
        assert response.headers.get(HX.RE_TARGET) is None
        assert response.headers.get(HX.TRIGGER_EVENT) is None


@pytest.mark.parametrize(
    "engine, template, expected",
    (
        (JinjaTemplateEngine, "path: {{ request.scope['path'] }}", "path: /"),
        (MakoTemplateEngine, "path: ${request.scope['path']}", "path: /"),
    ),
)
def test_HTMXTemplate_response_bad_trigger_params(
    engine: Any, template: str, expected: str, template_dir: Path
) -> None:
    Path(template_dir / "abc.html").write_text(template)

    @get(path="/", media_type=MediaType.HTML)
    def handler() -> HTMXTemplate:
        return HTMXTemplate(
            name="abc.html",
            context={"request": {"scope": {"path": "nope"}}},
            trigger_event="showMessage",
            params={"alert": "Confirm your Choice."},
            after="begin",  # type: ignore
        )

    with create_test_client(
        route_handlers=[handler],
        template_config=TemplateConfig(
            directory=template_dir,
            engine=engine,
        ),
    ) as client:
        response = client.get("/")
        error = response.json()
        assert (
            error["detail"]
            == "ValueError(\"Invalid value for after param. Value must be either 'receive', 'settle' or 'swap'.\")"
        )
        assert response.headers.get(HX.PUSH_URL) is None
        assert response.headers.get(HX.RE_SWAP) is None
        assert response.headers.get(HX.RE_TARGET) is None
        assert response.headers.get(HX.TRIGGER_EVENT) is None
