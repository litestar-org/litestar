=======
Plugins
=======

Litestar supports a plugin system that allows you to extend the functionality of the framework.

.. seealso:: * :doc:`/usage/databases/sqlalchemy/plugins/index`

Plugins are defined by :class:`protocols <typing.Protocol>` (see :pep:`544`) and any type that satisfies
a :class:`protocol <typing.Protocol>` can be included in the ``plugins`` argument of the
:class:`app <litestar.app.Litestar>`.

The following plugin protocols are defined:

1. :class:`InitPluginProtocol <litestar.plugins.InitPluginProtocol>`: This protocol defines a contract for plugins
that can interact with the data that is used to instantiate the application instance.

2. :class:`SerializationPluginProtocol <litestar.plugins.SerializationPluginProtocol>`: This protocol defines
the contract for plugins that extend serialization functionality of the application.

:class:`InitPluginProtocol <litestar.plugins.InitPluginProtocol>`
-----------------------------------------------------------------

:class:`InitPluginProtocol <litestar.plugins.InitPluginProtocol>` defines an interface that allows for customization
of the application's initialization process. Init plugins can define dependencies, add route handlers,
configure middleware, and much more!

Implementations of these plugins must define a single method:

:meth:`on_app_init() <litestar.plugins.InitPluginProtocol.on_app_init>`
-----------------------------------------------------------------------

This method accepts and must return an :class:`AppConfig <litestar.config.app.AppConfig>` instance,
which can be modified and is later used to instantiate the application.

.. code-block:: python
    :caption: :meth:`on_app_init() <litestar.plugins.InitPluginProtocol.on_app_init>` required method signature

    def on_app_init(self, app_config: AppConfig) -> AppConfig: ...

This method is invoked after any ``on_app_init`` hooks have been called, and each plugin is invoked in the order that
they are provided in the :paramref:`~litestar.app.Litestar.plugins` parameter of the
:class:`app <litestar.app.Litestar>`.

.. note:: Because of this, plugin authors should make it clear in their documentation if their plugin should be
    invoked before or after other plugins.

Simple Plugin Example
+++++++++++++++++++++

The following example shows a simple plugin that adds a route handler, and a dependency to the application.

.. literalinclude:: /examples/plugins/init_plugin_protocol.py
   :caption: ``InitPluginProtocol`` implementation example

The ``MyPlugin`` class is an implementation of the :class:`InitPluginProtocol <litestar.plugins.InitPluginProtocol>`. It
defines a single method, ``on_app_init()``, which takes an :class:`AppConfig <litestar.config.app.AppConfig>` instance
as an argument and returns same.

In the ``on_app_init()`` method, the dependency mapping is updated to include a new dependency named ``"name"``, which
is provided by the ``get_name()`` function, and :paramref:`~litestar.config.app.AppConfig.route_handlers` is updated to
include the ``route_handler()`` function.

The modified :class:`AppConfig <litestar.config.app.AppConfig>` instance is then returned.

:class:`~litestar.plugins.base.SerializationPluginProtocol`
-----------------------------------------------------------

The :class:`~litestar.plugins.base.SerializationPluginProtocol` defines a contract for plugins that provide serialization
functionality for data types that are otherwise unsupported by the framework.

Implementations of these plugins must define the following methods:

:meth:`supports_type() <litestar.plugins.SerializationPluginProtocol.supports_type>`
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

The method takes a :class:`FieldDefinition <litestar.typing.FieldDefinition>` instance as an argument and
returns a :class:`bool` indicating whether the plugin supports serialization for that type.

.. code-block:: python
    :caption: :meth:`supports_type() <litestar.plugins.SerializationPluginProtocol.supports_type>` required method signature

    def supports_type(self, field_definition: FieldDefinition) -> bool: ...

:meth:`~litestar.plugins.SerializationPluginProtocol.create_dto_for_type`
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

This method accepts a :class:`FieldDefinition <litestar.typing.FieldDefinition>` instance as an argument and must return a
:class:`AbstractDTO <litestar.dto.base_dto.AbstractDTO>` implementation that can be used to serialize and deserialize
the type.

.. code-block:: python
    :caption: :meth:`create_dto_for_type() <litestar.plugins.SerializationPluginProtocol.create_dto_for_type>` required
      method signature

      def create_dto_for_type(self, field_definition: FieldDefinition) -> type[AbstractDTO]: ...

During application startup, if a ``data`` or ``return`` annotation is encountered that is not a supported type,
is supported by the plugin, and does not otherwise have a ``dto`` or ``return_dto`` defined,
the plugin is used to create a DTO type for that annotation.

* :doc:`Learn more about DTOs </usage/dto/0-basic-use>`

Serialization Plugin Example
++++++++++++++++++++++++++++

The following example shows the actual implementation of the :class:`~litestar.plugins.base.SerializationPluginProtocol`
for `SQLAlchemy <https://www.sqlalchemy.org/>`_ models that is is provided in :doc:`advanced-alchemy:index`.

.. note:: Starting in v2.1.0 this references a stub that now points to the :doc:`advanced-alchemy:index` library.
    The example is still valid but the
    :class:`SQLAlchemySerializationPlugin <advanced_alchemy.extensions.litestar.plugins.serialization.SQLAlchemySerializationPlugin>`
    has moved as part of https://github.com/litestar-org/litestar/pull/2312.

.. dropdown:: Show Example

    .. code-block:: python
        :caption: Advanced Alchemy SQLAlchemy Serialization Plugin Example

        from __future__ import annotations

        from typing import TYPE_CHECKING, Any

        from litestar.plugins import SerializationPluginProtocol
        from sqlalchemy.orm import DeclarativeBase

        from advanced_alchemy.extensions.litestar.dto import SQLAlchemyDTO
        from advanced_alchemy.extensions.litestar.plugins import _slots_base

        if TYPE_CHECKING:
            from litestar.typing import FieldDefinition


        class SQLAlchemySerializationPlugin(SerializationPluginProtocol, _slots_base.SlotsBase):
            def __init__(self) -> None:
                self._type_dto_map: dict[type[DeclarativeBase], type[SQLAlchemyDTO[Any]]] = {}

            def supports_type(self, field_definition: FieldDefinition) -> bool:
                return (
                    field_definition.is_collection and field_definition.has_inner_subclass_of(DeclarativeBase)
                ) or field_definition.is_subclass_of(DeclarativeBase)

            def create_dto_for_type(self, field_definition: FieldDefinition) -> type[SQLAlchemyDTO[Any]]:
                # assumes that the type is a container of SQLAlchemy models or a single SQLAlchemy model
                annotation = next(
                    (
                        inner_type.annotation
                        for inner_type in field_definition.inner_types
                        if inner_type.is_subclass_of(DeclarativeBase)
                    ),
                    field_definition.annotation,
                )
                if annotation in self._type_dto_map:
                    return self._type_dto_map[annotation]

                self._type_dto_map[annotation] = dto_type = SQLAlchemyDTO[annotation]  # type:ignore[valid-type]

                return dto_type

* :meth:`supports_type() <advanced_alchemy.extensions.litestar.plugins.serialization.SQLAlchemySerializationPlugin.supports_type>`
  returns a :class:`bool` indicating whether the plugin supports serialization for the given type.
  Specifically, we return
  ``True`` if the parsed type is either a collection of SQLAlchemy models or a single SQLAlchemy model.

* :meth:`create_dto_for_type() <advanced_alchemy.extensions.litestar.plugins.serialization.SQLAlchemySerializationPlugin.create_dto_for_type>`
  takes a :class:`FieldDefinition <litestar.typing.FieldDefinition>` instance as an argument and returns a
  :class:`SQLAlchemyDTO <advanced_alchemy.extensions.litestar.dto.SQLAlchemyDTO>` subclass and includes some
  logic that may be interesting to potential serialization plugin authors.

The first thing the method does is check if the parsed type is a collection of SQLAlchemy models or a single SQLAlchemy
model, retrieves the model type in either case and assigns it to the ``annotation`` variable.

The method then checks if ``annotation`` is already in the ``_type_dto_map`` dictionary.
If it is, it returns the corresponding DTO type. This is done to ensure that multiple
:class:`SQLAlchemyDTO <advanced_alchemy.extensions.litestar.dto.SQLAlchemyDTO>`
subtypes are not created for the same model.

If the annotation is not in the ``_type_dto_map`` dictionary, the method creates a new DTO type for the annotation,
adds it to the ``_type_dto_map`` dictionary, and returns it.

:class:`~litestar.plugins.DIPlugin`
-----------------------------------

:class:`~litestar.plugins.DIPlugin` can be used to extend Litestar's dependency
injection by providing information about injectable types.

Its main purpose it to facilitate the injection of :term:`callables <python:callable>` with unknown signatures,
for example Pydantic's ``BaseModel`` classes; These are not supported natively since,
while they are callables, their type information is not contained within their callable
signature (their :func:`__init__` method).

.. literalinclude:: /examples/plugins/di_plugin.py
   :caption: Dynamically generating signature information for a custom type

.. toctree::
    :titlesonly:

    flash_messages
