# Plugins

Starlite supports extension through plugins, which allow for the following:

1. Serialization and deserialization of non-pydantic based 3rd party classes.
2. Automatic OpenAPI schema creation for 3rd party classes.

In other words, plugins allow for the parsing and validation of incoming data using non-pydantic classes, while still
retaining the type safety, parsing and validation of pydantic. Additionally they allow for seamless serialization and
schema generation.

## Creating Plugins

A plugin is a class that implements the `starlite.plugins.base.PluginProtocol`. To create a plugin, subclass
the `PluginProtocol` and pass to it the base class for which the plugin is for as a generic argument. You should then
implement the following methods specified by the protocol:

```python
from typing import Type, Any, Dict
from starlite import PluginProtocol
from pydantic import BaseModel


class MyClass:
    ...


class MyPlugin(PluginProtocol[MyClass]):
    """
    The class for which we create a plugin. For example, could be a base ORM class such as "Model" or "Document" etc.
    """

    ...

    def to_pydantic_model_class(
        self, model_class: Type[MyClass], **kwargs: Any
    ) -> Type[BaseModel]:
        """
        Given a model_class, convert it to a subclass of the pydantic BaseModel
        """
        ...

    @staticmethod
    def is_plugin_supported_type(value: Any) -> bool:
        """
        Given a value of indeterminate type, determine if this value is supported by the plugin by returning a bool.
        """
        ...

    def from_pydantic_model_instance(
        self, model_class: Type[MyClass], pydantic_model_instance: BaseModel
    ) -> MyClass:
        """
        Given an instance of a pydantic model created using a plugin's 'to_pydantic_model_class',
        return an instance of the class from which that pydantic model has been created.

        This class is passed in as the 'model_class' kwarg.
        """
        ...

    def to_dict(self, model_instance: MyClass) -> Dict[str, Any]:
        """
        Given an instance of a model supported by the plugin, return a dictionary of serializable values.
        """
        ...

    def from_dict(self, model_class: Type[MyClass], **kwargs: Any) -> MyClass:
        """
        Given a class supported by this plugin and a dict of values, create an instance of the class
        """
        ...
```
