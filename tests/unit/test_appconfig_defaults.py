from __future__ import annotations

from litestar import Litestar
from litestar.config.app import AppConfig
from litestar.config.response_cache import ResponseCacheConfig
from litestar.logging.config import LoggingConfig
from litestar.openapi.config import OpenAPIConfig
from litestar.types import Empty


class TestAppConfigDefaults:
    def test_appconfig_defaults_match_litestar_init(self) -> None:
        config = AppConfig()
        app_from_config = Litestar.from_config(config)
        app_direct = Litestar()

        assert type(app_from_config.logging_config) == type(app_direct.logging_config)
        assert isinstance(app_from_config.logging_config, LoggingConfig)
        assert isinstance(app_direct.logging_config, LoggingConfig)

        assert type(app_from_config.response_cache_config) == type(app_direct.response_cache_config)
        assert isinstance(app_from_config.response_cache_config, ResponseCacheConfig)
        assert isinstance(app_direct.response_cache_config, ResponseCacheConfig)

        assert type(app_from_config.openapi_config) == type(app_direct.openapi_config)
        assert isinstance(app_from_config.openapi_config, OpenAPIConfig)
        assert isinstance(app_direct.openapi_config, OpenAPIConfig)
        if app_from_config.openapi_config is not None and app_direct.openapi_config is not None:
            assert hasattr(app_from_config.openapi_config, "title") and hasattr(app_direct.openapi_config, "title")
            assert app_from_config.openapi_config.title == app_direct.openapi_config.title
        if app_from_config.openapi_config is not None and app_direct.openapi_config is not None:
            assert hasattr(app_from_config.openapi_config, "version") and hasattr(app_direct.openapi_config, "version")
            version1 = getattr(app_from_config.openapi_config, "version", None)
            version2 = getattr(app_direct.openapi_config, "version", None)
            assert version1 == version2

        assert app_from_config.request_max_body_size == app_direct.request_max_body_size
        assert app_from_config.request_max_body_size == 10_000_000

    def test_appconfig_raw_defaults(self) -> None:
        config = AppConfig()

        assert config.logging_config is Empty
        assert config.response_cache_config is None
        assert config.openapi_config is not None
        assert isinstance(config.openapi_config, OpenAPIConfig)
        assert config.request_max_body_size == 10_000_000

    def test_custom_values_preserved(self) -> None:
        custom_logging = LoggingConfig(version=1)
        custom_cache = ResponseCacheConfig(default_expiration=120)
        custom_openapi = OpenAPIConfig(title="Custom API", version="2.0.0")
        custom_body_size = 5_000_000

        config = AppConfig(
            logging_config=custom_logging,
            response_cache_config=custom_cache,
            openapi_config=custom_openapi,
            request_max_body_size=custom_body_size,
        )
        app_from_config = Litestar.from_config(config)

        app_direct = Litestar(
            logging_config=custom_logging,
            response_cache_config=custom_cache,
            openapi_config=custom_openapi,
            request_max_body_size=custom_body_size,
        )

        if app_from_config.logging_config is not None and app_direct.logging_config is not None:
            assert hasattr(app_from_config.logging_config, "version") and hasattr(app_direct.logging_config, "version")
            # Use getattr to safely access version attribute
            version1 = getattr(app_from_config.logging_config, "version", None)
            version2 = getattr(app_direct.logging_config, "version", None)
            assert version1 == version2 == 1

        if app_from_config.response_cache_config is not None and app_direct.response_cache_config is not None:
            assert hasattr(app_from_config.response_cache_config, "default_expiration") and hasattr(
                app_direct.response_cache_config, "default_expiration"
            )
            assert (
                app_from_config.response_cache_config.default_expiration
                == app_direct.response_cache_config.default_expiration
                == 120
            )

        if app_from_config.openapi_config is not None and app_direct.openapi_config is not None:
            assert hasattr(app_from_config.openapi_config, "title") and hasattr(app_direct.openapi_config, "title")
            assert app_from_config.openapi_config.title == app_direct.openapi_config.title == "Custom API"
        assert app_from_config.request_max_body_size == app_direct.request_max_body_size == 5_000_000

    def test_none_values_handled_correctly(self) -> None:
        config = AppConfig(logging_config=None, response_cache_config=None, openapi_config=None)
        app_from_config = Litestar.from_config(config)

        app_direct = Litestar(logging_config=None, response_cache_config=None, openapi_config=None)

        assert app_from_config.logging_config == app_direct.logging_config
        assert app_from_config.response_cache_config == app_direct.response_cache_config
        assert app_from_config.openapi_config == app_direct.openapi_config

    def test_functional_behavior_equality(self) -> None:
        config = AppConfig()
        app_from_config = Litestar.from_config(config)
        app_direct = Litestar()

        logger1 = app_from_config.get_logger("test")
        logger2 = app_direct.get_logger("test")
        assert logger1 is not None
        assert logger2 is not None
        assert type(logger1) == type(logger2)

        if app_from_config.openapi_config is not None and app_direct.openapi_config is not None:
            assert hasattr(app_from_config.openapi_config, "title") and hasattr(app_direct.openapi_config, "title")
            assert app_from_config.openapi_config.title == app_direct.openapi_config.title

        assert app_from_config.request_max_body_size == app_direct.request_max_body_size

    def test_backwards_compatibility(self) -> None:
        configs = [
            AppConfig(),
            AppConfig(debug=True),
            AppConfig(request_max_body_size=1_000_000),
            AppConfig(openapi_config=OpenAPIConfig(title="Test", version="1.0.0")),
        ]

        for config in configs:
            app = Litestar.from_config(config)
            assert app is not None
            assert hasattr(app, "logging_config")
            assert hasattr(app, "openapi_config")
            assert hasattr(app, "request_max_body_size")

    def test_edge_cases(self) -> None:
        config = AppConfig(
            openapi_config=OpenAPIConfig(title="", version=""),
        )
        app = Litestar.from_config(config)
        if app.openapi_config is not None:
            assert app.openapi_config.title == ""
            assert app.openapi_config.version == ""

        config = AppConfig(request_max_body_size=0)
        app = Litestar.from_config(config)
        assert app.request_max_body_size == 0

        config = AppConfig(request_max_body_size=1_000_000_000)
        app = Litestar.from_config(config)
        assert app.request_max_body_size == 1_000_000_000


class TestAppConfigMutationLogic:
    def test_empty_logging_config_becomes_loggingconfig(self) -> None:
        config = AppConfig()
        app = Litestar.from_config(config)

        assert isinstance(app.logging_config, LoggingConfig)
        assert app.logging_config.version == 1

    def test_none_response_cache_config_becomes_responsecacheconfig(self) -> None:
        config = AppConfig()
        app = Litestar.from_config(config)

        assert isinstance(app.response_cache_config, ResponseCacheConfig)
        assert app.response_cache_config.default_expiration == 60

    def test_empty_values_in_direct_init(self) -> None:
        app = Litestar(
            logging_config=Empty,
            response_cache_config=None,
            request_max_body_size=None,
        )

        assert isinstance(app.logging_config, LoggingConfig)
        assert isinstance(app.response_cache_config, ResponseCacheConfig)
        assert app.request_max_body_size is None


class TestAppConfigTypeAnnotations:
    def test_logging_config_type_annotation(self) -> None:
        import inspect

        sig = inspect.signature(AppConfig.__init__)
        param = sig.parameters["logging_config"]

        assert "EmptyType" in str(param.annotation)

    def test_request_max_body_size_type_annotation(self) -> None:
        import inspect

        sig = inspect.signature(AppConfig.__init__)
        param = sig.parameters["request_max_body_size"]

        assert "EmptyType" not in str(param.annotation)
        assert "int" in str(param.annotation)
