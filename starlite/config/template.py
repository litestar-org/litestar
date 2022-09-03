from typing import Any, Callable, List, Optional, Type, Union

from pydantic import BaseConfig, BaseModel, DirectoryPath

from starlite.template import TemplateEngineProtocol


class TemplateConfig(BaseModel):
    """Configuration for Templating.

    To enable templating, pass an instance of this class to the
    [Starlite][starlite.app.Starlite] constructor using the
    'template_config' key.
    """

    class Config(BaseConfig):
        arbitrary_types_allowed = True

    directory: Union[DirectoryPath, List[DirectoryPath]]
    """
        A directory or list of directories from which to serve templates.
    """
    engine: Type[TemplateEngineProtocol]
    """
        A template engine adhering to the [TemplateEngineProtocol][starlite.template.base.TemplateEngineProtocol].
    """
    engine_callback: Optional[Callable[[Any], Any]] = None
    """
        A callback function that allows modifying the instantiated templating protocol.
    """
