from typing import TYPE_CHECKING, List, Union

from starlite.exceptions import MissingDependencyException, TemplateNotFoundException
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
    def __init__(self, directory: Union["DirectoryPath", List["DirectoryPath"]]) -> None:
        """Jinja2 based TemplateEngine.

        Args:
            directory: Direct path or list of directory paths from which to serve templates.
        """
        super().__init__(directory)
        loader = FileSystemLoader(searchpath=directory)
        self.engine = Environment(loader=loader, autoescape=True)

    def get_template(self, template_name: str) -> JinjaTemplate:
        """
        Retrieves a template by matching its name (dotted path) with files in the directory or directories provided.
        Args:
            template_name: A dotted path

        Returns:
            JinjaTemplate instance

        Raises:
            [TemplateNotFoundException][starlite.exceptions.TemplateNotFoundException]
        """
        try:
            return self.engine.get_template(name=template_name)
        except JinjaTemplateNotFound as exc:
            raise TemplateNotFoundException(template_name=template_name) from exc
