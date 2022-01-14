from typing import Any, Dict, List, NamedTuple, Optional, TypeVar, get_args

from pydantic import BaseModel
from typing_extensions import Protocol, Type, runtime_checkable

T = TypeVar("T", contravariant=True)


@runtime_checkable
class PluginProtocol(Protocol[T]):
    def to_pydantic_model_class(self, model_class: Type[T], **kwargs: Any) -> Type[BaseModel]:  # pragma: no cover
        """
        Given a model_class T, convert it to a pydantic model class
        """
        ...

    @staticmethod
    def is_plugin_supported_type(value: Any) -> bool:
        """
        Given a value of indeterminate type, determine if this value is supported by the plugin.
        """
        ...

    def from_pydantic_model_instance(self, model_class: Type[T], pydantic_model_instance: BaseModel) -> T:
        """
        Given a dict of parsed values, create an instance of the plugin's model class
        """
        ...

    def to_dict(self, model_instance: T) -> Dict[str, Any]:
        """
        Given an instance of the model, return a dictionary of values that can be serialized
        """
        ...


def get_plugin_for_value(value: Any, plugins: List[PluginProtocol]) -> Optional[PluginProtocol]:
    """Helper function to returns a plugin to handle a given value, if any plugin supports it"""
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
