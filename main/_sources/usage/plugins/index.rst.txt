.. _plugins:

=======
Plugins
=======

Litestar supports a plugin system that allows you to extend the functionality of the framework.


Plugins are defined by protocols, and any type that satisfies a protocol can be included in the ``plugins`` argument of
the :class:`app <litestar.app.Litestar>`.


InitPlugin
----------

``InitPlugin`` defines an interface that allows for customization of the application's initialization process.
Init plugins can define dependencies, add route handlers, configure middleware, and much more!

Implementations of these plugins must define a single method:
:meth:`on_app_init(self, app_config: AppConfig) -> AppConfig: <litestar.plugins.InitPlugin.on_app_init>`

The method accepts and must return an :class:`AppConfig <litestar.config.app.AppConfig>` instance, which can be modified
and is later used to instantiate the application.

This method is invoked after any ``on_app_init`` hooks have been called, and each plugin is invoked in the order that
they are provided in the ``plugins`` argument of the :class:`app <litestar.app.Litestar>`. Because of this, plugin
authors should make it clear in their documentation if their plugin should be invoked before or after other plugins.

Example
+++++++

The following example shows a simple plugin that adds a route handler, and a dependency to the application.

.. literalinclude:: /examples/plugins/init_plugin_protocol.py
   :language: python
   :caption: ``InitPlugin`` implementation example

The ``MyPlugin`` class is an implementation of the :class:`InitPlugin <litestar.plugins.InitPlugin>`. It
defines a single method, ``on_app_init()``, which takes an :class:`AppConfig <litestar.config.app.AppConfig>` instance
as an argument and returns same.

In the ``on_app_init()`` method, the dependency mapping is updated to include a new dependency named ``"name"``, which
is provided by the ``get_name()`` function, and ``route_handlers`` is updated to include the ``route_handler()``
function. The modified :class:`AppConfig <litestar.config.app.AppConfig>` instance is then returned.

SerializationPlugin
---------------------------

The :class:`~litestar.plugins.SerializationPlugin` defines a contract for plugins that
provide serialization functionality for data types that are otherwise unsupported by the
framework.

Implementations of these plugins must define the following methods.

1. :meth:`supports_type(self, field_definition: FieldDefinition) -> bool: <litestar.plugins.SerializationPlugin>`

The method takes a :class:`FieldDefinition <litestar.typing.FieldDefinition>` instance as an argument and returns a :class:`bool`
indicating whether the plugin supports serialization for that type.

2. :meth:`create_dto_for_type(self, field_definition: FieldDefinition) -> type[AbstractDTO]: <litestar.plugins.SerializationPlugin.create_dto_for_type>`

This method accepts a :class:`FieldDefinition <litestar.typing.FieldDefinition>` instance as an argument and must return a
:class:`AbstractDTO <litestar.dto.base_dto.AbstractDTO>` implementation that can be used to serialize and deserialize
the type.

During application startup, if a data or return annotation is encountered that is not a supported type, is supported by
the plugin, and doesn't otherwise have a ``dto`` or ``return_dto`` defined, the plugin is used to create a DTO type for
that annotation.

Example
+++++++

The following example shows the implementation pattern of a ``SerializationPlugin`` for
`SQLAlchemy <https://www.sqlalchemy.org/>`_ models. For the actual implementation, see the
``advanced_alchemy`` library documentation.

:meth:`supports_type(self, field_definition: FieldDefinition) -> bool: <advanced_alchemy.extensions.litestar.SQLAlchemySerializationPlugin.supports_type>`
returns a :class:`bool` indicating whether the plugin supports serialization for the given type. Specifically, we return
``True`` if the parsed type is either a collection of SQLAlchemy models or a single SQLAlchemy model.

:meth:`create_dto_for_type(self, field_definition: FieldDefinition) -> type[AbstractDTO]: <advanced_alchemy.extensions.litestar.SQLAlchemySerializationPlugin.create_dto_for_type>`
takes a :class:`FieldDefinition <litestar.typing.FieldDefinition>` instance as an argument and returns a
:class:`SQLAlchemyDTO <advanced_alchemy.extensions.litestar.dto.SQLAlchemyDTO>` subclass and includes some logic that may be
interesting to potential serialization plugin authors.

The first thing the method does is check if the parsed type is a collection of SQLAlchemy models or a single SQLAlchemy
model, retrieves the model type in either case and assigns it to the ``annotation`` variable.

The method then checks if ``annotation`` is already in the ``_type_dto_map`` dictionary. If it is, it returns the
corresponding DTO type. This is done to ensure that multiple :class:`SQLAlchemyDTO <advanced_alchemy.extensions.litestar.dto.SQLAlchemyDTO>`
subtypes are not created for the same model.

If the annotation is not in the ``_type_dto_map`` dictionary, the method creates a new DTO type for the annotation,
adds it to the ``_type_dto_map`` dictionary, and returns it.


DIPlugin
--------

:class:`~litestar.plugins.DIPlugin` can be used to extend Litestar's dependency
injection by providing information about injectable types.

Its main purpose it to facilitate the injection of callables with unknown signatures,
for example Pydantic's ``BaseModel`` classes; These are not supported natively since,
while they are callables, their type information is not contained within their callable
signature (their :func:`__init__` method).


.. literalinclude:: /examples/plugins/di_plugin.py
   :language: python
   :caption: Dynamically generating signature information for a custom type

.. toctree::
    :titlesonly:

    flash_messages
    problem_details


ReceiveRoutePlugin
------------------

:class:`~litestar.plugins.ReceiveRoutePlugin` allows you to receive routes as they are registered on the application.
This can be useful for plugins that need to perform actions based on the routes being added, such as generating
documentation, validating route configurations, or tracking route statistics.

Implementations of this plugin must define a single method:
:meth:`receive_route(self, route: BaseRoute) -> None: <litestar.plugins.ReceiveRoutePlugin.receive_route>`

The method receives a :class:`BaseRoute <litestar.routes.BaseRoute>` instance as routes are registered on the application.
This happens during the application initialization process, after routes are created but before the application starts.

Example
+++++++

The following example shows a simple plugin that logs information about each route as it's registered:

.. code-block:: python

    from litestar.plugins import ReceiveRoutePlugin
    from litestar.routes import BaseRoute

    class RouteLoggerPlugin(ReceiveRoutePlugin):
        def receive_route(self, route: BaseRoute) -> None:
            print(f"Route registered: {route.path} [{', '.join(route.methods)}]")
