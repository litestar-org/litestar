.. _updating:

Updating instances
------------------

In this section we'll see how to update existing instances using :class:`DTOData <litestar.dto.factory.DTOData>`.

PUT handlers
============

`PUT <https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/PUT>`_ requests are characterized by requiring the
full data model to be submitted for update.

.. literalinclude:: /examples/data_transfer_objects/factory/tutorial/put_handlers.py
   :language: python
   :linenos:
   :emphasize-lines: 26,29,30

This script defines a ``PUT`` handler with path ``/person/{person_id:int}`` that includes a route parameter,
``person_id`` to specify which person should be updated.

In the handler, we create an instance of ``Person``, simulating a database lookup, and then pass it to the
:meth:`DTOData.update_instance() <litestar.dto.factory.DTOData.update_instance>` method, which returns the same instance
after modifying it with the submitted data.

.. image:: images/put_handlers.png
    :align: center

PATCH handlers
==============

`PATCH <https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/PATCH>`_ requests are characterized by allowing any
subset of the properties of the data model to be submitted for update. This is in contrast to
`PUT <https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/PUT>`_ requests, which require the entire data model
to be submitted.

.. literalinclude:: /examples/data_transfer_objects/factory/tutorial/patch_handlers.py
   :language: python
   :linenos:
   :emphasize-lines: 22,23,26

In this latest update, the handler has been changed to a :class:`@patch() <litestar.handlers.patch>`
handler.

This script introduces the ``PatchDTO`` class that has a similar configuration to ``WriteDTO``, with the ``id`` field
excluded, but it also sets :attr:`partial=True <litestar.dto.factory.DTOConfig.partial>`. This setting allows for
partial updates of the resource.

And here's a demonstration of use:

.. image:: images/patch_handlers.png
    :align: center
