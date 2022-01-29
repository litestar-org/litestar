from typing import List, Union

from pydantic import DirectoryPath

from starlite.exceptions import MissingDependencyException, TemplateNotFound
from starlite.template.base import TemplateEngineProtocol

try:
    from jinja2 import Environment, FileSystemLoader
    from jinja2 import Template as JinjaTemplate
    from jinja2 import TemplateNotFound as JinjaTemplateNotFound
except ImportError as exc:  # pragma: no cover
    raise MissingDependencyException("jinja2 is not installed") from exc


class JinjaTemplateEngine(TemplateEngineProtocol[JinjaTemplate]):
    def __init__(self, directory: Union[DirectoryPath, List[DirectoryPath]]) -> None:
        loader = FileSystemLoader(searchpath=directory)
        self.engine = Environment(loader=loader, autoescape=True)

    def get_template(self, name: str) -> JinjaTemplate:
        """Loads the template with the name and returns it."""
        try:
            return self.engine.get_template(name=name)
        except JinjaTemplateNotFound as e:
            raise TemplateNotFound(template_name=name) from e
