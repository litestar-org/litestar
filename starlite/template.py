# pylint: disable=E0401, C0415
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, cast

from pydantic import DirectoryPath
from typing_extensions import Protocol, runtime_checkable

from starlite.exceptions import MissingDependencyException, TemplateNotFound


@runtime_checkable
class AbstractTemplate(Protocol):
    def render(self, **context: Optional[Dict[str, Any]]) -> str:
        """Returns the rendered template as a string"""


class AbstractTemplateEngine(ABC):
    @abstractmethod
    def __init__(self, directory: Union[DirectoryPath, List[DirectoryPath]]) -> None:
        """Builds a template engine."""

    @abstractmethod
    def get_template(self, name: str) -> AbstractTemplate:
        """Loads the template with name and returns it."""


class JinjaTemplateEngine(AbstractTemplateEngine):
    __slots__ = ["_engine"]

    def __init__(self, directory: Union[DirectoryPath, List[DirectoryPath]]) -> None:
        try:
            import jinja2
        except ImportError as e:  # pragma: no cover
            raise MissingDependencyException("jinja2 is not installed") from e

        loader = jinja2.FileSystemLoader(searchpath=directory)
        self._engine = jinja2.Environment(loader=loader, autoescape=True)

    def get_template(self, name: str) -> AbstractTemplate:
        from jinja2 import TemplateNotFound as JinjaTemplateNotFound

        try:
            return cast(AbstractTemplate, self._engine.get_template(name=name))
        except JinjaTemplateNotFound as e:
            raise TemplateNotFound(template_name=name) from e


class MakoTemplateEngine(AbstractTemplateEngine):
    __slots__ = ["_engine"]

    def __init__(self, directory: Union[DirectoryPath, List[DirectoryPath]]) -> None:
        try:
            from mako.lookup import TemplateLookup
        except ImportError as e:  # pragma: no cover
            raise MissingDependencyException("mako is not installed") from e

        self._engine = TemplateLookup(directories=[directory])

    def get_template(self, name: str) -> AbstractTemplate:
        from mako.exceptions import TemplateLookupException as MakoTemplateNotFound

        try:
            return cast(AbstractTemplate, self._engine.get_template(name))
        except MakoTemplateNotFound as e:
            raise TemplateNotFound(template_name=name) from e
