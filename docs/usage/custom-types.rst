Custom types
=============

Data serialization / deserialization (encoding / decoding) and validation are important parts of any API framework.

Among others, litestar supports Python's builtin dataclasses, Pydantic and msgspec for these tasks, defaulting to msgspec with json as serialization protocol.

While msgspec supports `a lot of types <https://jcristharif.com/msgspec/supported-types.html>`_, sometimes you may need to employ a custom type. Msgspec provides an `extension mechanism <https://jcristharif.com/msgspec/extending.html#mapping-to-from-native-types>`_ where you provide encoding and decoding hook functions which translate your type in a type that msgspec knows.

Litestar supports this mechanism via ``type_encoders`` and ``type_decoders`` :term:`parameters <parameter>` which can be defined on every layer. For example see the :doc:`litestar app reference </reference/app>`.


.. admonition:: Layered architecture

    ``type_encoders`` and ``type_decoders`` are part of Litestar's layered architecture, which means you can set them on every layer of the application. If you set them on multiple layers,
    the layer closest to the route handler will take precedence.

    You can read more about this here:
    :ref:`Layered architecture <usage/applications:layered architecture>`

Here is an example:


.. literalinclude:: /examples/encoding_decoding/custom_type_encoding_decoding.py
   :caption: Tell Litestar how to encode and decode a custom type
