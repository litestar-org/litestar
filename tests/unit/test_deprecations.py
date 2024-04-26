import importlib

import pytest

from litestar.types.asgi_types import ASGIApp


@pytest.mark.parametrize(
    "import_path, import_name",
    (
        (
            "litestar.contrib.repository",
            "AbstractAsyncRepository",
        ),
        (
            "litestar.contrib.repository",
            "AbstractSyncRepository",
        ),
        (
            "litestar.contrib.repository",
            "ConflictError",
        ),
        (
            "litestar.contrib.repository",
            "FilterTypes",
        ),
        (
            "litestar.contrib.repository",
            "NotFoundError",
        ),
        (
            "litestar.contrib.repository",
            "RepositoryError",
        ),
        (
            "litestar.contrib.repository.exceptions",
            "ConflictError",
        ),
        (
            "litestar.contrib.repository.exceptions",
            "NotFoundError",
        ),
        (
            "litestar.contrib.repository.exceptions",
            "RepositoryError",
        ),
        (
            "litestar.contrib.repository.filters",
            "BeforeAfter",
        ),
        (
            "litestar.contrib.repository.filters",
            "CollectionFilter",
        ),
        (
            "litestar.contrib.repository.filters",
            "FilterTypes",
        ),
        (
            "litestar.contrib.repository.filters",
            "LimitOffset",
        ),
        (
            "litestar.contrib.repository.filters",
            "OrderBy",
        ),
        (
            "litestar.contrib.repository.filters",
            "SearchFilter",
        ),
        (
            "litestar.contrib.repository.filters",
            "NotInCollectionFilter",
        ),
        (
            "litestar.contrib.repository.filters",
            "OnBeforeAfter",
        ),
        (
            "litestar.contrib.repository.filters",
            "NotInSearchFilter",
        ),
        (
            "litestar.contrib.repository.handlers",
            "signature_namespace_values",
        ),
        (
            "litestar.contrib.repository.handlers",
            "on_app_init",
        ),
        (
            "litestar.contrib.repository.testing",
            "GenericAsyncMockRepository",
        ),
    ),
)
def test_repository_deprecations(import_path: str, import_name: str) -> None:
    module = importlib.import_module(import_path)
    assert getattr(module, import_name)


def test_litestar_type_deprecation() -> None:
    with pytest.warns(DeprecationWarning):
        from litestar.types.internal_types import LitestarType  # noqa: F401


def test_contrib_minijnja_deprecation() -> None:
    with pytest.warns(DeprecationWarning):
        from litestar.contrib.minijnja import MiniJinjaTemplateEngine  # noqa: F401


def test_litestar_templates_template_context_deprecation() -> None:
    with pytest.warns(DeprecationWarning):
        from litestar.template.base import TemplateContext  # noqa: F401


def test_minijinja_from_state_deprecation() -> None:
    with pytest.warns(DeprecationWarning):
        from litestar.contrib.minijinja import minijinja_from_state  # noqa: F401


def test_constants_deprecations() -> None:
    with pytest.warns(DeprecationWarning):
        from litestar.constants import SCOPE_STATE_NAMESPACE  # noqa: F401


def test_utils_deprecations() -> None:
    with pytest.warns(DeprecationWarning):
        from litestar.utils import (  # noqa: F401
            delete_litestar_scope_state,
            get_litestar_scope_state,
            set_litestar_scope_state,
        )


def test_utils_scope_deprecations() -> None:
    with pytest.warns(DeprecationWarning):
        from litestar.utils.scope import (  # noqa: F401
            delete_litestar_scope_state,
            get_litestar_scope_state,
            set_litestar_scope_state,
        )


def test_is_sync_or_async_generator_deprecation() -> None:
    with pytest.warns(DeprecationWarning):
        from litestar.utils.predicates import is_sync_or_async_generator  # noqa: F401

    with pytest.warns(DeprecationWarning):
        from litestar.utils import is_sync_or_async_generator as _  # noqa: F401


def test_openapi_config_openapi_controller_deprecation() -> None:
    from litestar.openapi.config import OpenAPIConfig
    from litestar.openapi.controller import OpenAPIController

    with pytest.warns(DeprecationWarning):
        OpenAPIConfig(title="API", version="1.0", openapi_controller=OpenAPIController)


def test_openapi_config_root_schema_site_deprecation() -> None:
    from litestar.openapi.config import OpenAPIConfig

    with pytest.warns(DeprecationWarning):
        OpenAPIConfig(title="API", version="1.0", root_schema_site="redoc")


def test_openapi_config_enabled_endpoints_deprecation() -> None:
    from litestar.openapi.config import OpenAPIConfig

    with pytest.warns(DeprecationWarning):
        OpenAPIConfig(title="API", version="1.0", enabled_endpoints={"redoc"})


def test_cors_middleware_public_interface_deprecation() -> None:
    with pytest.warns(DeprecationWarning):
        from litestar.middleware.cors import CORSMiddleware  # noqa: F401


def test_exception_handler_middleware_debug_deprecation(mock_asgi_app: ASGIApp) -> None:
    from litestar.middleware._internal.exceptions import ExceptionHandlerMiddleware

    with pytest.warns(DeprecationWarning):
        ExceptionHandlerMiddleware(mock_asgi_app, debug=True)


def test_exception_handler_middleware_exception_handlers_deprecation(mock_asgi_app: ASGIApp) -> None:
    from litestar.middleware._internal.exceptions import ExceptionHandlerMiddleware

    with pytest.warns(DeprecationWarning):
        ExceptionHandlerMiddleware(mock_asgi_app, debug=None, exception_handlers={})


def test_deprecate_exception_handler_middleware() -> None:
    with pytest.warns(DeprecationWarning):
        from litestar.middleware.exceptions import ExceptionHandlerMiddleware  # noqa: F401

    with pytest.raises(ImportError):
        from litestar.middleware.exceptions.middleware import OtherName  # noqa: F401


def test_deprecate_exception_handler_middleware_2() -> None:
    with pytest.warns(DeprecationWarning):
        from litestar.middleware.exceptions.middleware import ExceptionHandlerMiddleware  # noqa: F401

    with pytest.raises(ImportError):
        from litestar.middleware.exceptions import OtherName  # noqa: F401


def test_deprecate_create_debug_response() -> None:
    with pytest.warns(DeprecationWarning):
        from litestar.middleware.exceptions._debug_response import create_debug_response  # noqa: F401

    with pytest.raises(ImportError):
        from litestar.middleware.exceptions._debug_response import OtherName  # noqa: F401


def test_deprecate_create_exception_response() -> None:
    with pytest.warns(DeprecationWarning):
        from litestar.middleware.exceptions.middleware import create_exception_response  # noqa: F401

    with pytest.raises(ImportError):
        from litestar.middleware.exceptions.middleware import OtherName  # noqa: F401


def test_deprecate_exception_response_content() -> None:
    with pytest.warns(DeprecationWarning):
        from litestar.middleware.exceptions.middleware import ExceptionResponseContent  # noqa: F401

    with pytest.raises(ImportError):
        from litestar.middleware.exceptions.middleware import OtherName  # noqa: F401
