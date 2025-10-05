SQLAlchemy Serialization Plugin
-------------------------------

The SQLAlchemy Serialization Plugin allows Litestar to do the work of transforming inbound and outbound data to and from
SQLAlchemy models. The plugin takes no arguments, simply instantiate it and pass it to your application.

Example
=======

.. tab-set::

   .. tab-item:: Async

        .. literalinclude:: /examples/sqla/plugins/sqlalchemy_async_serialization_plugin.py
            :caption: SQLAlchemy Async Serialization Plugin
            :language: python
            :linenos:

   .. tab-item:: Sync

        .. literalinclude:: /examples/sqla/plugins/sqlalchemy_sync_serialization_plugin.py
            :caption: SQLAlchemy Sync Serialization Plugin
            :language: python
            :linenos:

How it works
============

The plugin works by defining a :class:`SQLAlchemyDTO <advanced_alchemy.extensions.litestar.dto.SQLAlchemyDTO>` class for each
handler ``data`` or return annotation that is a SQLAlchemy model, or collection of SQLAlchemy models, that isn't
otherwise managed by an explicitly defined DTO class.

The following two examples are functionally equivalent:

.. tab-set::

   .. tab-item:: Serialization Plugin

        .. literalinclude:: /examples/sqla/plugins/sqlalchemy_async_serialization_plugin.py
            :language: python
            :linenos:

   .. tab-item:: Data Transfer Object

        .. literalinclude:: /examples/sqla/plugins/sqlalchemy_async_serialization_dto.py
            :language: python
            :linenos:

During registration, the application recognizes that there is no DTO class explicitly defined and determines that the
handler annotations are supported by the SQLAlchemy Serialization Plugin. The plugin is then used to generate a DTO
class for both the ``data`` keyword argument and the return annotation.

Configuring data transfer
#########################

As the serialization plugin merely defines DTOs for the handler, we can
:ref:`mark the model fields <dto-marking-fields>` to control the data that we allow in and out of
our application.

.. tab-set::

   .. tab-item:: Async

        .. literalinclude:: /examples/sqla/plugins/sqlalchemy_async_serialization_plugin_marking_fields.py
            :caption: SQLAlchemy Async Marking Fields
            :language: python
            :linenos:
            :emphasize-lines: 10,23

   .. tab-item:: Sync

        .. literalinclude:: /examples/sqla/plugins/sqlalchemy_sync_serialization_plugin_marking_fields.py
            :caption: SQLAlchemy Sync Marking Fields
            :language: python
            :linenos:
            :emphasize-lines: 10,23

In the above example, a new attribute called ``super_secret_value`` has been added to the model, and a value set for it
in the handler. However, due to "marking" the field as "private", when the model is serialized, the value is not present
in the response.
