from typing import TYPE_CHECKING, List, Union

from starlite.exceptions import MissingDependencyException, TemplateNotFound
from starlite.template.base import TemplateEngineProtocol

if TYPE_CHECKING:
    from pydantic import DirectoryPath

try:
    from mako.exceptions import TemplateLookupException as MakoTemplateNotFound
    from mako.lookup import TemplateLookup
    from mako.template import Template as MakoTemplate
except ImportError as e:
    raise MissingDependencyException("mako is not installed") from e


class MakoTemplateEngine(TemplateEngineProtocol[MakoTemplate]):
    """Template engine using the mako templating library"""

    def __init__(self, directory: Union["DirectoryPath", List["DirectoryPath"]]) -> None:
        super().__init__(directory)
        self.engine = TemplateLookup(directories=directory if isinstance(directory, (list, tuple)) else [directory])

    def get_template(self, name: str) -> MakoTemplate:
        """Loads the template with the name and returns it."""
        try:
            return self.engine.get_template(name)
        except MakoTemplateNotFound as exc:
            raise TemplateNotFound(template_name=name) from exc
