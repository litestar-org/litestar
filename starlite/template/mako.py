from typing import TYPE_CHECKING, List, Union

from starlite.exceptions import MissingDependencyException, TemplateNotFoundException
from starlite.template.base import TemplateEngineProtocol

if TYPE_CHECKING:
    from pydantic import DirectoryPath

try:
    from mako.exceptions import TemplateLookupException as MakoTemplateNotFound
    from mako.lookup import TemplateLookup
    from mako.template import Template as MakoTemplate
except ImportError as exc:
    raise MissingDependencyException("mako is not installed") from exc


class MakoTemplateEngine(TemplateEngineProtocol[MakoTemplate]):
    def __init__(self, directory: Union["DirectoryPath", List["DirectoryPath"]]) -> None:
        """Mako based TemplateEngine.

        Args:
            directory: Direct path or list of directory paths from which to serve templates.
        """
        super().__init__(directory)
        self.engine = TemplateLookup(directories=directory if isinstance(directory, (list, tuple)) else [directory])

    def get_template(self, template_name: str) -> MakoTemplate:
        """
        Retrieves a template by matching its name (dotted path) with files in the directory or directories provided.
        Args:
            template_name: A dotted path

        Returns:
            MakoTemplate instance

        Raises:
            [TemplateNotFoundException][starlite.exceptions.TemplateNotFoundException]
        """
        try:
            return self.engine.get_template(template_name)
        except MakoTemplateNotFound as e:
            raise TemplateNotFoundException(template_name=template_name) from e
