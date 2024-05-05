Plugins
=======

Starlite supports extension through plugins, which allow for the following:


1. Updating the :doc:`Starlite application </usage/the-starlite-app>` during the init process
2. Serialization and deserialization of non-pydantic based 3rd party classes
3. Automatic OpenAPI schema creation for 3rd party classes

Thus, plugins allow for a wide range of actions - from registering middleware to the parsing and validation of incoming
data using non-pydantic classes. Additionally, they allow for seamless serialization and schema generation.

Creating Plugins
----------------

A plugin is a class that implements the :class:`PluginProtocol <starlite.plugins.base.PluginProtocol>`.

If you wish to support the serialization and deserialization of none-pydantic classes, you need to implement the
following methods specified by the:

.. code-block:: python

   from typing import Type, Any, Dict
   from starlite import PluginProtocol
   from pydantic import BaseModel


   class MyClass: ...


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
           Given an instance of a pydantic model created using a plugin's ``to_pydantic_model_class``,
           return an instance of the class from which that pydantic model has been created.

           This class is passed in as the ``model_class`` kwarg.
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

If you wish to register middlewares, guards, dependencies and so forth on the application init, you need to implement the
:meth:`on_app_init <starlite.plugins.base.PluginProtocol.on_app_init>` method:

.. code-block:: python

   from typing import Any
   from starlite import PluginProtocol, Starlite, get


   @get("/some-path")
   def my_handler() -> None: ...


   class MyPlugin(PluginProtocol[Any]):
       def on_app_init(self, app: Starlite) -> None:
           # register a route handler
           app.register(my_handler)

           # update attributes of the application before init is finished.
           app.after_request = ...
           app.after_response = ...
           app.before_request = ...
           app.dependencies.update({...})
           app.exception_handlers.update({...})
           app.guards.extend(...)
           app.middleware.extend(...)
           app.on_shutdown.extend(...)
           app.on_startup.extend(...)
           app.parameters.update({...})
           app.response_class = ...
           app.response_cookies.extend(...)
           app.response_headers.update(...)
           app.tags.extend(...)


.. toctree::
    :titlesonly:
    :hidden:

    piccolo-orm
    sqlalchemy
    tortoise-orm
