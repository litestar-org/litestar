from typing import List, Union

from pydantic import DirectoryPath

from starlite.exceptions import MissingDependencyException, TemplateNotFound
from starlite.template.base import ProtocolEngine

try:
    from jinja2 import Environment, FileSystemLoader, Template
    from jinja2 import TemplateNotFound as JinjaTemplateNotFound
except ImportError as exc:  # pragma: no cover
    raise MissingDependencyException("jinja2 is not installed") from exc


class JinjaTemplateEngine(ProtocolEngine[Template]):
    def __init__(self, directory: Union[DirectoryPath, List[DirectoryPath]]) -> None:
        loader = FileSystemLoader(searchpath=directory)
        self._engine = Environment(loader=loader, autoescape=True)

    def get_template(self, name: str) -> Template:
        """Loads the template with the name and returns it."""
        try:
            return self._engine.get_template(name=name)
        except JinjaTemplateNotFound as e:
            raise TemplateNotFound(template_name=name) from e
