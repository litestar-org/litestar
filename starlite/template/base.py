from typing import Any, Dict, List, Optional, TypeVar, Union

from pydantic import DirectoryPath, validate_arguments
from typing_extensions import Protocol, runtime_checkable


@runtime_checkable
class TemplateProtocol(Protocol):  # pragma: no cover
    """Protocol for a templating engine's class"""

    def render(self, **context: Optional[Dict[str, Any]]) -> str:
        """Returns the rendered template as a string"""


T_co = TypeVar("T_co", bound=TemplateProtocol, covariant=True)


@runtime_checkable
class TemplateEngineProtocol(Protocol[T_co]):  # pragma: no cover
    """Protocol for a template engine"""

    @validate_arguments
    def __init__(self, directory: Union[DirectoryPath, List[DirectoryPath]]) -> None:
        ...

    def get_template(self, name: str) -> T_co:
        """Loads the template with name and returns it"""
