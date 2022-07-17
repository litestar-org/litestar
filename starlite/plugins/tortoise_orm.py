from typing import TYPE_CHECKING, Any, Dict, Type, cast

from starlite import MissingDependencyException
from starlite.plugins.base import PluginProtocol

try:
    from tortoise import Model
    from tortoise.contrib.pydantic import PydanticModel as TortoisePydanticModel
    from tortoise.contrib.pydantic import pydantic_model_creator
except ImportError as e:
    raise MissingDependencyException("tortoise-orm is not installed") from e

if TYPE_CHECKING:
    from pydantic import BaseModel


class TortoiseORMPlugin(PluginProtocol[Model]):
    def to_pydantic_model_class(self, model_class: Type[Model], **kwargs: Any) -> Type[TortoisePydanticModel]:
        """
        Given a model_class T, convert it to a subclass of the pydantic BaseModel
        """
        return cast(Type[TortoisePydanticModel], pydantic_model_creator(model_class, **kwargs))

    @staticmethod
    def is_plugin_supported_type(value: Any) -> bool:
        """
        Given a value of indeterminate type, determine if this value is supported by the plugin.
        """
        return isinstance(value, Model)

    def from_pydantic_model_instance(self, model_class: Type[Model], pydantic_model_instance: "BaseModel") -> Model:
        """
        Given an instance of a pydantic model created using a plugin's 'to_pydantic_model_class',
        return an instance of the class from which that pydantic model has been created.

        This class is passed in as the 'model_class' kwarg.
        """
        return model_class().update_from_dict(pydantic_model_instance.dict())

    def to_dict(self, model_instance: Model) -> Dict[str, Any]:
        """
        Given an instance of a model supported by the plugin, return a dictionary of serializable values.
        """
        fields: Dict[str, Any] = {}
        for field_name, value in model_instance:
            fields[field_name] = value
        return fields

    def from_dict(self, model_class: Type[Model], **kwargs: Any) -> Model:
        """
        Given a class supported by this plugin and a dict of values, create an instance of the class
        """
        return model_class().update_from_dict(**kwargs)
