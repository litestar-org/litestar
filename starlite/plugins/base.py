from typing import Any, Dict, List, NamedTuple, Optional, TypeVar

from pydantic import BaseModel
from typing_extensions import Protocol, Type, get_args, runtime_checkable

T = TypeVar("T")


@runtime_checkable
class PluginProtocol(Protocol[T]):  # pragma: no cover
    def to_pydantic_model_class(self, model_class: Type[T], **kwargs: Any) -> Type[BaseModel]:  # pragma: no cover
        """
        Given a model_class T, convert it to a subclass of the pydantic BaseModel
        """

    @staticmethod
    def is_plugin_supported_type(value: Any) -> bool:
        """
        Given a value of indeterminate type, determine if this value is supported by the plugin.
        """

    def from_pydantic_model_instance(self, model_class: Type[T], pydantic_model_instance: BaseModel) -> T:
        """
        Given an instance of a pydantic model created using a plugin's 'to_pydantic_model_class',
        return an instance of the class from which that pydantic model has been created.

        This class is passed in as the 'model_class' kwarg.
        """

    def to_dict(self, model_instance: T) -> Dict[str, Any]:
        """
        Given an instance of a model supported by the plugin, return a dictionary of serializable values.
        """

    def from_dict(self, model_class: Type[T], **kwargs: Any) -> T:
        """
        Given a class supported by this plugin and a dict of values, create an instance of the class
        """


def get_plugin_for_value(value: Any, plugins: List[PluginProtocol]) -> Optional[PluginProtocol]:
    """Helper function to returns a plugin to handle a given value, if any plugin supports it"""
    if plugins:
        if value and isinstance(value, (list, tuple)):
            value = value[0]
        if get_args(value):
            value = get_args(value)[0]
        for plugin in plugins:
            if plugin.is_plugin_supported_type(value):
                return plugin
    return None


class PluginMapping(NamedTuple):
    plugin: PluginProtocol
    model_class: Any
