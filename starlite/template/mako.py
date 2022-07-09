from __future__ import annotations

from typing import TYPE_CHECKING

from starlite.exceptions import MissingDependencyException, TemplateNotFound
from starlite.template.base import TemplateEngineProtocol

if TYPE_CHECKING:
    from pydantic import DirectoryPath

try:
    from mako.exceptions import TemplateLookupException as MakoTemplateNotFound
    from mako.lookup import TemplateLookup
    from mako.template import Template as MakoTemplate
except ImportError as exc:  # pragma: no cover
    raise MissingDependencyException("mako is not installed") from exc


class MakoTemplateEngine(TemplateEngineProtocol[MakoTemplate]):
    """Template engine using the mako templating library"""

    def __init__(self, directory: DirectoryPath | list[DirectoryPath]) -> None:
        super().__init__(directory)
        self.engine = TemplateLookup(directories=directory if isinstance(directory, (list, tuple)) else [directory])

    def get_template(self, name: str) -> MakoTemplate:
        """Loads the template with the name and returns it."""
        try:
            return self.engine.get_template(name)
        except MakoTemplateNotFound as e:
            raise TemplateNotFound(template_name=name) from e
