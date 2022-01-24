from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, TypeVar, Union, cast

from pydantic import DirectoryPath
from typing_extensions import Protocol, runtime_checkable

from starlite.exceptions import MissingDependencyException

F = TypeVar("F", bound=Callable[..., Any])


@runtime_checkable
class AbstractTemplate(Protocol):
    def render(self, context: Dict[str, Any]) -> str:
        """Returns the rendered template as a string"""
        ...


class AbstractTemplateEngine(ABC):
    @abstractmethod
    def __init__(self, directory: Union[DirectoryPath, List[DirectoryPath]]) -> None:
        ...

    @abstractmethod
    def get_template(self, name: str) -> AbstractTemplate:
        """Loads the template with name and returns it."""
        ...


class JinjaTemplateEngine(AbstractTemplateEngine):
    __slots__ = ["_engine"]

    def __init__(self, directory: Union[DirectoryPath, List[DirectoryPath]]) -> None:
        try:
            import jinja2  # pylint: disable=C0415
        except ImportError as e:
            raise MissingDependencyException("jinja2 is not installed") from e

        loader = jinja2.FileSystemLoader(searchpath=directory)
        self._engine = jinja2.Environment(loader=loader, autoescape=True)

    def get_template(self, name: str) -> AbstractTemplate:
        return cast(AbstractTemplate, self._engine.get_template(name=name))


class MakoTemplateEngine(AbstractTemplateEngine):
    __slots__ = ["_engine"]

    def __init__(self, directory: Union[DirectoryPath, List[DirectoryPath]]) -> None:
        try:
            from mako.lookup import TemplateLookup  # pylint: disable=C0415
        except ImportError as e:
            raise MissingDependencyException("mako is not installed") from e

        self._engine = TemplateLookup([directory])

    def get_template(self, name: str) -> AbstractTemplate:
        return cast(AbstractTemplate, self._engine.get_template(name))
