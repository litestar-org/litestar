from inspect import isclass
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
)

from pydantic import BaseConfig, DirectoryPath, PrivateAttr, root_validator
from pydantic.generics import GenericModel

from starlite.template import TemplateEngineProtocol

T = TypeVar("T", bound=TemplateEngineProtocol)


class TemplateConfig(Generic[T], GenericModel):
    """Configuration for Templating.

    To enable templating, pass an instance of this class to the [Starlite][starlite.app.Starlite] constructor using the
    'template_config' key.
    """

    class Config(BaseConfig):
        arbitrary_types_allowed = True

    directory: Optional[Union[DirectoryPath, List[DirectoryPath]]] = None
    """A directory or list of directories from which to serve templates."""
    engine: Union[Type[T], T]
    """A template engine adhering to the [TemplateEngineProtocol][starlite.template.base.TemplateEngineProtocol]."""
    engine_callback: Optional[Callable[[T], None]] = None
    """A callback function that allows modifying the instantiated templating protocol."""
    _engine_instance: T = PrivateAttr()

    @root_validator
    def validate_config(cls, values: Dict[str, Any]) -> Dict[str, Any]:  # pylint: disable=E0213
        """Ensure that directory is set if engine is a class.

        Args:
            values: The dictionary of values to validate

        Returns:
            The validated dictionary of values.
        """
        if isclass(values.get("engine")) and not values.get("directory"):
            raise ValueError("directory is a required kwarg when passing a template engine class")
        return values

    def to_engine(self) -> T:
        """Instantiate the template engine."""
        template_engine = cast("T", self.engine(self.directory) if isclass(self.engine) else self.engine)
        if callable(self.engine_callback):
            self.engine_callback(template_engine)  # pylint: disable=E1102
        self._engine_instance = template_engine
        return template_engine

    @property
    def engine_instance(self) -> T:
        """Return the template engine instance."""
        if not hasattr(self, "_engine_instance"):
            return self.to_engine()
        return self._engine_instance
