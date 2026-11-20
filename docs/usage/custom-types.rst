Custom types
============

Data serialization / deserialization (encoding / decoding) and validation are important parts of any API framework.

In addition to being capable to encode / decode and validate many standard types, litestar supports Python's builtin dataclasses and libraries like Pydantic and msgspec.

However, sometimes you may need to employ a custom type.

Using type encoders / decoders
------------------------------

Litestar supports a mechanism where you provide encoding and decoding hook functions which translate your type in / to a type that it knows. You can provide them via the ``type_encoders`` and ``type_decoders`` :term:`parameters <parameter>` which can be defined on every layer. For example see the :doc:`litestar app reference </reference/app>`.

.. admonition:: Layered architecture

    ``type_encoders`` and ``type_decoders`` are part of Litestar's layered architecture, which means you can set them on every layer of the application. If you set them on multiple layers,
    the layer closest to the route handler will take precedence.

    You can read more about this here:
    :ref:`Layered architecture <usage/applications:layered architecture>`

Here is an example:

.. literalinclude:: /examples/encoding_decoding/custom_type_encoding_decoding.py
   :language: python
   :caption: Tell Litestar how to encode and decode a custom type

Encoding-specific type encoders
-------------------------------

When the result of an encoder is only valid for one encoding, for example pre-encoded bytes wrapped in
:class:`msgspec.Raw`, use :class:`~litestar.serialization.TypeEncoder` to provide a dedicated callable per encoding.
Encodings without a dedicated callable fall back to the ``default`` one.

.. literalinclude:: /examples/encoding_decoding/encoding_specific_type_encoder.py
   :language: python
   :caption: Use a different encoder for JSON and MessagePack

Litestar's own Pydantic integration uses this to let Pydantic serialize models straight to JSON, while still
producing a regular ``dict`` for MessagePack responses.

.. note::

    If you pass a serializer to a ``msgspec`` encoder yourself, bind it to the target encoding with
    ``get_serializer(type_encoders, encoding="json")``. :func:`~litestar.serialization.encode_json` and
    :func:`~litestar.serialization.encode_msgpack` do this for you when given the result of
    :func:`~litestar.serialization.get_serializer`. Binding to the wrong encoding is not detected.

Custom Pydantic types
---------------------

If you use a custom Pydantic type you can use it directly:

.. literalinclude:: /examples/encoding_decoding/custom_type_pydantic.py
   :language: python
   :caption: Tell Litestar how to encode and decode a custom Pydantic type
