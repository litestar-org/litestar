import inspect
from typing import List
from unittest.mock import MagicMock, PropertyMock

import pytest

from starlite import LoggingConfig
from starlite.app import DEFAULT_CACHE_CONFIG, Starlite
from starlite.config.app import AppConfig
from starlite.router import Router


@pytest.fixture()
def app_config_object() -> AppConfig:
    return AppConfig(
        after_exception=[],
        after_request=None,
        after_response=None,
        after_shutdown=[],
        after_startup=[],
        allowed_hosts=[],
        before_request=None,
        before_send=[],
        before_shutdown=[],
        before_startup=[],
        cache_config=DEFAULT_CACHE_CONFIG,
        cache_control=None,
        compression_config=None,
        cors_config=None,
        csrf_config=None,
        debug=False,
        dependencies={},
        exception_handlers={},
        guards=[],
        initial_state={},
        logging_config=None,
        middleware=[],
        multipart_form_part_limit=1000,
        on_shutdown=[],
        on_startup=[],
        openapi_config=None,
        opt={},
        parameters={},
        plugins=[],
        response_class=None,
        response_cookies=[],
        response_headers={},
        route_handlers=[],
        security=[],
        static_files_config=[],
        tags=[],
        template_config=None,
        request_class=None,
        websocket_class=None,
        etag=None,
    )


def test_app_params_defined_on_app_config_object() -> None:
    """Ensures that all parameters to the `Starlite` constructor are present on the `AppConfig` object."""
    starlite_signature = inspect.signature(Starlite)
    app_config_fields = AppConfig.__fields__
    for name in starlite_signature.parameters:
        if name in ("on_app_init", "initial_state"):
            continue
        assert name in app_config_fields
    # ensure there are not fields defined on AppConfig that aren't in the Starlite signature
    assert not (app_config_fields.keys() - starlite_signature.parameters.keys())


def test_app_config_object_used(app_config_object: AppConfig, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure that the properties on the `AppConfig` object are accessed within the `Starlite` constructor.

    In the test we replace every field on the `AppConfig` type with a property mock so that we can check that it has at
    least been accessed. It doesn't actually check that we do the right thing with it, but is a guard against the case
    of adding a parameter to the `Starlite` signature and to the `AppConfig` object, and using the value from the
    parameter downstream from construction of the `AppConfig` object.
    """

    # replace each field on the `AppConfig` object with a `PropertyMock`, this allows us to assert that the properties
    # have been accessed during app instantiation.
    property_mocks: List[PropertyMock] = []
    for name in AppConfig.__fields__:
        if name == "cache_config":
            property_mock = PropertyMock(return_value=DEFAULT_CACHE_CONFIG)
        else:
            # default iterable return value allows the mock properties that need to be iterated over in
            # `Starlite.__init__()` to not blow up, for other properties it shouldn't matter what the value is for the
            # sake of this test.
            property_mock = PropertyMock(return_value=[])
        property_mocks.append(property_mock)
        monkeypatch.setattr(type(app_config_object), name, property_mock, raising=False)

    # Things that we don't actually need to call for this test
    monkeypatch.setattr(Starlite, "register", MagicMock())
    monkeypatch.setattr(Starlite, "_create_asgi_handler", MagicMock())
    monkeypatch.setattr(Router, "__init__", MagicMock())

    # instantiates the app with an `on_app_config` that returns our patched `AppConfig` object.
    Starlite(route_handlers=[], on_app_init=[MagicMock(return_value=app_config_object)])

    # this ensures that each of the properties of the `AppConfig` object have been accessed within `Starlite.__init__()`
    for mock in property_mocks:
        mock.assert_called()


def test_app_debug_create_logger() -> None:
    app = Starlite([], debug=True)

    assert app.logging_config
    assert app.logging_config.loggers["starlite"]["level"] == "DEBUG"  # type: ignore[attr-defined]


def test_app_debug_explicitly_disable_logging() -> None:
    app = Starlite([], debug=True, logging_config=None)

    assert not app.logging_config


def test_app_debug_update_logging_config() -> None:
    logging_config = LoggingConfig()
    app = Starlite([], debug=True, logging_config=logging_config)

    assert app.logging_config is logging_config
    assert app.logging_config.loggers["starlite"]["level"] == "DEBUG"  # type: ignore[attr-defined]


def test_set_initial_state() -> None:
    def set_initial_state_in_hook(app_config: AppConfig) -> AppConfig:
        assert isinstance(app_config.initial_state, dict)
        app_config.initial_state["c"] = "D"  # pyright:ignore
        app_config.initial_state["e"] = "f"  # pyright:ignore
        return app_config

    app = Starlite(route_handlers=[], initial_state={"a": "b", "c": "d"}, on_app_init=[set_initial_state_in_hook])
    assert app.state._state == {"a": "b", "c": "D", "e": "f"}
