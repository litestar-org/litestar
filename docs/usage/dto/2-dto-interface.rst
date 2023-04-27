DTO Interface
=============

While Litestar maintains a suite of DTO factories, it is possible to create your own DTOs. To do so, you must implement
the :class:`DTOInterface <litestar.dto.interface.DTOInterface>` protocol.

The following is a description of the methods of the protocol, and how they are used by Litestar. For detailed
information on the signature of each method, see the :class:`reference docs <litestar.dto.interface.DTOInterface>`.

Abstract Methods
~~~~~~~~~~~~~~~~

These methods must be implemented on any :class:`DTOInterface <litestar.dto.interface.DTOInterface>` subtype.

data_to_encodable_type
----------------------

This method receives the data that is returned from a handler and is responsible for converting it to a type that
Litestar can encode to bytes, or bytes. Litestar calls this method with data returned from the route handler in order
to generate the response payload.

bytes_to_data_type
------------------

This method receives raw bytes, as received from the client connection.

The DTO instance is responsible for parsing those bytes into the appropriate data type for the handler. This method is
called for all requests that do not specify URL or multipart encoded form data.

The return value is injected into the handler as the ``data`` argument.

builtins_to_data_type
---------------------

This method receives data that has already been parsed into primitive python types (``list``, ``dict``, ``int``, etc)
but has not yet been validated according to the model type declarations.

This method is only called when the handler receives URL encoded, or multipart form data. In this case, the data is
first parsed from the request body into primitive types and then passed to this method.

The return value of this method is injected into the handler as the ``data`` argument.

Additional Methods
~~~~~~~~~~~~~~~~~~

The following methods have default implementations on the :class:`DTOInterface <litestar.dto.interface.DTOInterface>`
types, but can be overridden if necessary.

__init__
--------

A DTO instance is created for each use per connection. The ``__init__`` method receives an instance of
:class:`ConnectionContext <litestar.dto.interface.ConnectionContext>` which contains information about the connection
such as the ID of the handler that is being called and the request encoding type.

create_openapi_schema
---------------------

This method is called when generating the OpenAPI schema for the handler. It should return an instance of
:class:`Schema <litestar.openapi.spec.Schema>` that reflects the data accepted by, or returned from the handler.

on_registration
---------------

This class method is called for each handler that the DTO type is registered upon. It receives an instance of
:class:`HandlerContext <litestar.dto.interface.HandlerContext>` which contains information about the handler and the
DTOs application including whether the DTO is being applied to "data" or "return" type of the handler, the type
annotation, the handler ID and request encoding for the handler.

DTO implementations should use the type annotation information to confirm that the DTO is being applied to a supported
type.
