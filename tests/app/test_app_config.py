import inspect
from typing import List
from unittest.mock import MagicMock, PropertyMock

import pytest

from starlite.app import DEFAULT_CACHE_CONFIG, Starlite
from starlite.config.app import AppConfig
from starlite.router import Router


@pytest.fixture()
def app_config_object() -> AppConfig:
    return AppConfig(
        route_handlers=[],
        after_exception=None,
        after_request=None,
        after_response=None,
        after_shutdown=None,
        after_startup=None,
        allowed_hosts=None,
        before_request=None,
        before_send=None,
        before_shutdown=None,
        before_startup=None,
        cache_config=DEFAULT_CACHE_CONFIG,
        compression_config=None,
        cors_config=None,
        csrf_config=None,
        debug=False,
        dependencies=None,
        exception_handlers=None,
        guards=None,
        middleware=None,
        on_shutdown=None,
        on_startup=None,
        openapi_config=None,
        parameters=None,
        plugins=None,
        response_class=None,
        response_cookies=None,
        response_headers=None,
        security=None,
        static_files_config=None,
        tags=None,
        template_config=None,
    )


@pytest.fixture()
def starlite_signature() -> inspect.Signature:
    return inspect.signature(Starlite)


def test_app_params_defined_on_app_config_object(starlite_signature: inspect.Signature) -> None:
    """Ensures that all parameters to the `Starlite` constructor are present on
    the `AppConfig` object."""
    app_config_fields = AppConfig.__fields__
    for name in starlite_signature.parameters:
        if name == "on_app_config":
            continue
        assert name in app_config_fields
    # ensure there are not fields defined on AppConfig that aren't in the Starlite signature
    assert not (app_config_fields.keys() - starlite_signature.parameters.keys())


def test_app_config_object_used(
    starlite_signature: inspect.Signature,
    app_config_object: AppConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure that the properties on the `AppConfig` object are accessed within
    the `Starlite` constructor."""

    # replace each field on the `AppConfig` object with a `PropertyMock`, this allows us to assert that the properties
    # have been accessed during app instantiation.
    property_mocks: List[PropertyMock] = []
    for name in AppConfig.__fields__:
        if name == "cache_config":
            return_value = DEFAULT_CACHE_CONFIG
        else:
            return_value = None
        property_mock = PropertyMock(return_value=return_value)
        property_mocks.append(property_mock)
        monkeypatch.setattr(type(app_config_object), name, property_mock, raising=False)

    # Patch methods called from within `Starlite.__init__()` to prevent various errors.
    monkeypatch.setattr(Starlite, "register", MagicMock())
    monkeypatch.setattr(Starlite, "_create_asgi_handler", MagicMock())
    monkeypatch.setattr(Router, "__init__", MagicMock())

    # instantiates the app with an `on_app_config` that returns our patched `AppConfig` object.
    Starlite(route_handlers=[], debug=False, on_app_config=[MagicMock(return_value=app_config_object)])

    # this ensures that each of the properties of the `AppConfig` object have been accessed within `Starlite.__init__()`
    for mock in property_mocks:
        mock.assert_called()
