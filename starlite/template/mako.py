from typing import List, Union

from pydantic import DirectoryPath

from starlite.exceptions import MissingDependencyException, TemplateNotFound
from starlite.template.base import TemplateEngineProtocol

try:
    from mako.exceptions import TemplateLookupException as MakoTemplateNotFound
    from mako.lookup import TemplateLookup
    from mako.template import Template as MakoTemplate
except ImportError as exc:  # pragma: no cover
    raise MissingDependencyException("mako is not installed") from exc


class MakoTemplateEngine(TemplateEngineProtocol[MakoTemplate]):
    def __init__(self, directory: Union[DirectoryPath, List[DirectoryPath]]) -> None:
        self.engine = TemplateLookup(directories=[directory])

    def get_template(self, name: str) -> MakoTemplate:
        """Loads the template with the name and returns it."""
        try:
            return self.engine.get_template(name)
        except MakoTemplateNotFound as e:
            raise TemplateNotFound(template_name=name) from e
