Implementing Custom DTO Classes
===============================

While Litestar maintains a suite of DTO factories, it is possible to create your own DTOs. To do so, you must implement
the :class:`AbstractDTO <litestar.dto.base_dto.AbstractDTO>` abc.

The following is a description of the methods of the protocol, and how they are used by Litestar. For detailed
information on the signature of each method, see the :class:`reference docs <litestar.dto.base_dto.AbstractDTO>`.

Abstract Methods
~~~~~~~~~~~~~~~~

These methods must be implemented on any :class:`AbstractDTO <litestar.dto.base_dto.AbstractDTO>` subtype.

``generate_field_definitions``
------------------------------

This method receives the model type for the DTO and it should return a generator yielding
:class:`DTOFieldDefinition<litestar.dto.data_structures.DTOFieldDefinition>` instances corresponding with
the model fields.

``detect_nested_field``
-----------------------

This method receives a :class:`FieldDefinition<litestar.typing.FieldDefinition>` instance and it should return a boolean
indicating whether the field is a nested model field.

Deprecated entry points
~~~~~~~~~~~~~~~~~~~~~~~

.. deprecated:: 3.0
    :meth:`AbstractDTO.__init__ <litestar.dto.base_dto.AbstractDTO.__init__>`,
    :meth:`~litestar.dto.base_dto.AbstractDTO.decode_bytes`,
    :meth:`~litestar.dto.base_dto.AbstractDTO.decode_builtins`,
    :meth:`~litestar.dto.base_dto.AbstractDTO.data_to_encodable_type` and
    :meth:`~litestar.dto.base_dto.AbstractDTO.create_for_field_definition` are deprecated and will be removed in 4.0.
    :meth:`~litestar.dto.base_dto.AbstractDTO.create_openapi_schema` is deprecated and keeps working for tools that
    pass ``handler.handler_id``.

A DTO is applied through a plan that is built when its route handler is registered, and a DTO class is not
instantiated per request.

Overriding :meth:`~litestar.dto.base_dto.AbstractDTO.decode_bytes`,
:meth:`~litestar.dto.base_dto.AbstractDTO.decode_builtins`,
:meth:`~litestar.dto.base_dto.AbstractDTO.data_to_encodable_type`,
:meth:`~litestar.dto.base_dto.AbstractDTO.create_for_field_definition` or
:meth:`~litestar.dto.base_dto.AbstractDTO.create_openapi_schema` keeps working and emits no warning: the overriding
method is still called, and a replacement hook will be provided before these members are removed in 4.0. Calling the
base implementations directly, outside such an override, emits a deprecation warning.

The two abstract methods above and the class-level hooks
:meth:`~litestar.dto.base_dto.AbstractDTO.get_config_for_model_type`,
:attr:`~litestar.dto.base_dto.AbstractDTO.attribute_accessor`,
:meth:`~litestar.dto.base_dto.AbstractDTO.get_model_type_hints`,
:meth:`~litestar.dto.base_dto.AbstractDTO.get_model_namespace`,
:meth:`~litestar.dto.base_dto.AbstractDTO.get_property_fields`,
:meth:`~litestar.dto.base_dto.AbstractDTO.resolve_model_type` and
:meth:`~litestar.dto.base_dto.AbstractDTO.is_supported_model_type_field` remain the extension surface.
