.. _patch-handlers:

PATCH handlers
---------------

Updating existing instances is supported with the :class:`DTOData <litestar.dto.factory.DTOData>` class.
`PATCH <https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/PATCH>`_ requests are characterized by allowing any
subset of the properties of the data model to be submitted for update. This is in contrast to
`PUT <https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/PUT>`_ requests, which require the entire data model
to be submitted.

.. literalinclude:: /examples/data_transfer_objects/factory/tutorial/patch_handlers.py
   :language: python
   :linenos:
   :emphasize-lines: 22,23,26,29,30

In this latest update, the handler has been changed to a :class:`@patch() <litestar.handlers.http_handlers.patch>`
handler, and receives a path parameter called ``person_id``.

In order for our DTO to know that we don't require the full representation of the ``Person`` to be submitted by the
client we create ``PatchDTO`` and set the ``partial=True`` configuration.

In the handler, we create an instance of ``Person``, simulating a database lookup, and then pass it to the
:meth:`DTOData.update_instance() <litestar.dto.factory.DTOData.update_instance>` method, which returns the same instance
after modifying it with the submitted data.

And here's the result:

.. image:: images/patch_handlers.png
    :align: center

Notice that the name of the ``Person`` instance created in the handler is ``John``, but the name of the ``Person``
returned from the handler is ``Peter``.
