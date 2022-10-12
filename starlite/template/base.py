from typing import TYPE_CHECKING, Any, List, Mapping, TypeVar, Union, cast

from pydantic import DirectoryPath, validate_arguments
from typing_extensions import Protocol, runtime_checkable

if TYPE_CHECKING:
    from starlite import Request


def url_for(context: Mapping[str, Any], route_name: str, **path_parameters: Any) -> str:
    """Wrapper for [route_reverse][starlite.app.route_reverse] to be used in
    templates.

    Args:
        name: A route handler unique name.
        **path_parameters: Actual values for path parameters in the route.

    Raises:
        NoRouteMatchFoundException: If path parameters are missing in **path_parameters or have wrong type.

    Returns:
        A fully formatted url path.
    """
    request = cast("Request", context.get("request"))
    return request.app.route_reverse(route_name, **path_parameters)


class TemplateProtocol(Protocol):  # pragma: no cover
    """Protocol Defining a 'Template'.

    Template is a class that has a render method which renders the
    template into a string.
    """

    def render(self, *args: Any, **kwargs: Any) -> str:
        """Returns the rendered template as a string.

        Args:
            **kwargs: A string keyed mapping of values passed to the TemplateEngine

        Returns:
            The rendered template string
        """
        ...


T_co = TypeVar("T_co", bound=TemplateProtocol, covariant=True)


@runtime_checkable
class TemplateEngineProtocol(Protocol[T_co]):  # pragma: no cover
    @validate_arguments
    def __init__(self, directory: Union[DirectoryPath, List[DirectoryPath]]) -> None:
        """Protocol for a templating engine.

        Args:
            directory: Direct path or list of directory paths from which to serve templates.
        """
        ...

    def get_template(self, template_name: str) -> T_co:
        """
        Retrieves a template by matching its name (dotted path) with files in the directory or directories provided.
        Args:
            template_name: A dotted path

        Returns:
            Template instance

        Raises:
            [TemplateNotFoundException][starlite.exceptions.TemplateNotFoundException]: if no template is found.
        """
        ...
