from typing import List, Union

from pydantic import DirectoryPath

from starlite.exceptions import TemplateNotFound
from starlite.extras import MAKO
from starlite.template.base import TemplateEngineProtocol

with MAKO:
    # pylint: disable=import-error
    from mako.exceptions import TemplateLookupException as MakoTemplateNotFound
    from mako.lookup import TemplateLookup
    from mako.template import Template as MakoTemplate


class MakoTemplateEngine(TemplateEngineProtocol[MakoTemplate]):
    """Template engine using the mako templating library"""

    def __init__(self, directory: Union[DirectoryPath, List[DirectoryPath]]) -> None:
        super().__init__(directory)
        self.engine = TemplateLookup(directories=directory if isinstance(directory, (list, tuple)) else [directory])

    def get_template(self, name: str) -> MakoTemplate:
        """Loads the template with the name and returns it."""
        try:
            return self.engine.get_template(name)
        except MakoTemplateNotFound as e:
            raise TemplateNotFound(template_name=name) from e
