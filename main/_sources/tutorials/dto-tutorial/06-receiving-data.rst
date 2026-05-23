Receiving data
--------------

So far, we've only returned data to the client, however, this is only half of the story. We also need to be able to
control the data that we receive from the client.

Here's the code we'll use to start:

.. literalinclude:: /examples/data_transfer_objects/factory/tutorial/simple_receiving_data.py
   :language: python
   :linenos:

To simplify our demonstration, we've reduced our data model back down to a single ``Person`` class, with ``name``
``age`` and ``email`` attributes.

As before, ``ReadDTO`` is configured for the handler, and excludes the ``email`` attribute from return payloads.

Our handler is now a :class:`@post() <litestar.handlers.post>` handler, that is annotated to both accept and return an
instance of ``Person``.

Litestar can natively decode request payloads into Python :func:`dataclasses <dataclasses.dataclass>`, so we don't
*need* a DTO defined for the inbound data for this script to work.

Now that we need to send data to the server to test our program, you can use a tool like
`Postman <https://www.postman.com/>`_ or `Posting <https://github.com/darrenburns/posting?tab=readme-ov-file#posting>`_. Here's an example of a request/response payload:

.. image:: images/simple_receive_data.png
    :align: center
