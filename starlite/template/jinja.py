from typing import TYPE_CHECKING, List, Union

from starlite.exceptions import MissingDependencyException, TemplateNotFound
from starlite.template.base import TemplateEngineProtocol

if TYPE_CHECKING:
    from pydantic import DirectoryPath

try:
    from jinja2 import Environment, FileSystemLoader
    from jinja2 import Template as JinjaTemplate
    from jinja2 import TemplateNotFound as JinjaTemplateNotFound
except ImportError as e:
    raise MissingDependencyException("jinja2 is not installed") from e


class JinjaTemplateEngine(TemplateEngineProtocol[JinjaTemplate]):
    """Template engine using the jinja templating library"""

    def __init__(self, directory: Union["DirectoryPath", List["DirectoryPath"]]) -> None:
        super().__init__(directory)
        loader = FileSystemLoader(searchpath=directory)
        self.engine = Environment(loader=loader, autoescape=True)

    def get_template(self, name: str) -> JinjaTemplate:
        """Loads the template with the name and returns it."""
        try:
            return self.engine.get_template(name=name)
        except JinjaTemplateNotFound as exc:
            raise TemplateNotFound(template_name=name) from exc
