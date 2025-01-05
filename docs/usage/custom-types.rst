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

Custom Pydantic types
---------------------

If you use a custom Pydantic type you can use it directly:

.. literalinclude:: /examples/encoding_decoding/custom_type_pydantic.py
   :language: python
   :caption: Tell Litestar how to encode and decode a custom Pydantic type
