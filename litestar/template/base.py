from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Protocol, TypedDict, TypeVar, runtime_checkable

__all__ = (
    "TemplateContext",
    "TemplateEngineProtocol",
    "TemplateProtocol",
    "csrf_token",
    "url_for",
    "url_for_static_asset",
)


if TYPE_CHECKING:
    from pydantic import DirectoryPath

    from litestar.connection import Request


class TemplateContext(TypedDict):
    """Dictionary representing a template context."""

    request: Request[Any, Any, Any]
    csrf_input: str


def url_for(context: TemplateContext, route_name: str, **path_parameters: Any) -> str:
    """Wrap :func:`route_reverse <litestar.app.route_reverse>` to be used in templates.

    Args:
        context: The template context.
        route_name: The name of the route handler.
        **path_parameters: Actual values for path parameters in the route.

    Raises:
        NoRouteMatchFoundException: If ``route_name`` does not exist, path parameters are missing in **path_parameters or have wrong type.

    Returns:
        A fully formatted url path.
    """
    return context["request"].app.route_reverse(route_name, **path_parameters)


def csrf_token(context: TemplateContext) -> str:
    """Set a CSRF token on the template.

    Notes:
        - to use this function make sure to pass an instance of :ref:`CSRFConfig <litestar.config.csrf_config.CSRFConfig>` to
        the :class:`Litestar <litestar.app.Litestar>` constructor.

    Args:
        context: The template context.

    Returns:
        A CSRF token if the app level ``csrf_config`` is set, otherwise an empty string.
    """
    return context["request"].scope.get("_csrf_token", "")  # type: ignore


def url_for_static_asset(context: TemplateContext, name: str, file_path: str) -> str:
    """Wrap :meth:`url_for_static_asset <litestar.app.url_for_static_asset>` to be used in templates.

    Args:
        context: The template context object.
        name: A static handler unique name.
        file_path: a string containing path to an asset.

    Raises:
        NoRouteMatchFoundException: If static files handler with ``name`` does not exist.

    Returns:
        A url path to the asset.
    """
    return context["request"].app.url_for_static_asset(name, file_path)


class TemplateProtocol(Protocol):  # pragma: no cover
    """Protocol Defining a ``Template``.

    Template is a class that has a render method which renders the template into a string.
    """

    def render(self, *args: Any, **kwargs: Any) -> str:
        """Return the rendered template as a string.

        Args:
            *args: Positional arguments passed to the TemplateEngine
            **kwargs: A string keyed mapping of values passed to the TemplateEngine

        Returns:
            The rendered template string
        """
        ...


T_co = TypeVar("T_co", bound=TemplateProtocol, covariant=True)


@runtime_checkable
class TemplateEngineProtocol(Protocol[T_co]):  # pragma: no cover
    """Protocol for template engines."""

    def __init__(self, directory: DirectoryPath | list[DirectoryPath] | None, engine_instance: Any | None) -> None:
        """Initialize the template engine with a directory.

        Args:
            directory: Direct path or list of directory paths from which to serve templates, if provided the implementation has to create the engine instance.
            engine_instance: A template engine object, if provided the implementation has to use it.
        """
        ...

    def get_template(self, template_name: str) -> T_co:
        """Retrieve a template by matching its name (dotted path) with files in the directory or directories provided.

        Args:
            template_name: A dotted path

        Returns:
            Template instance

        Raises:
            TemplateNotFoundException: if no template is found.
        """
        ...

    def register_template_callable(self, key: str, template_callable: Callable[[dict[str, Any]], Any]) -> None:
        """Register a callable on the template engine.

        Args:
            key: The callable key, i.e. the value to use inside the template to call the callable.
            template_callable: A callable to register.

        Returns:
            None
        """
