Life Cycle Hooks
================

Life cycle hooks allow the execution of a callable at a certain point during the request-response
cycle. The hooks available are:

+--------------------------------------+------------------------------------+
| Name                                 | Runs                               |
+======================================+====================================+
| `before_request`_                    | Before the router handler function |
+--------------------------------------+------------------------------------+
| `after_request`_                     | After the route handler function   |
+--------------------------------------+------------------------------------+
| `after_response`_                    | After the response has been sent   |
+--------------------------------------+------------------------------------+

.. _before_request:

Before Request
--------------

The ``before_request`` hook runs immediately before calling the route handler function. It
can be any callable accepting a :class:`~litestar.connection.Request` as its first parameter
and returns either ``None`` or a value that can be used in a response.
If a value is returned, the router handler for this request will be bypassed.

.. literalinclude:: /examples/lifecycle_hooks/before_request.py
    :language: python


.. _after_request:

After Request
-------------

The ``after_request`` hook runs after the route handler returned and the response object
has been resolved. It can be any callable which takes a :class:`~litestar.response.Response`
instance as its first parameter, and returns a ``Response`` instance. The ``Response``
instance returned does not necessarily have to be the one that was received.

.. literalinclude:: /examples/lifecycle_hooks/after_request.py
    :language: python


.. _after_response:

After Response
--------------

The ``after_response`` hook runs after the response has been returned by the server.
It can be any callable accepting a :class:`~litestar.connection.Request` as its first parameter
and does not return any value.

This hook is meant for data post-processing, transmission of data to third party
services, gathering of metrics, etc.

.. literalinclude:: /examples/lifecycle_hooks/after_response.py
    :language: python


.. note::

    Since the request has already been returned by the time the ``after_response`` is called,
    the updated state of ``COUNTER`` is not reflected in the response.


Layered hooks
-------------

.. admonition:: Layered architecture

    Life cycle hooks are part of Litestar's layered architecture, which means you can
    set them on every layer of the application. If you set hooks on multiple layers,
    the layer closest to the route handler will take precedence.

    You can read more about this here:
    :ref:`Layered architecture <usage/applications:layered architecture>`


.. literalinclude:: /examples/lifecycle_hooks/layered_hooks.py
   :language: python
