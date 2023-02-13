Middleware
==========

Middlewares in Starlite are ASGI apps that are called "in the middle" between the application entrypoint and the
route handler function.

Starlite ships with several builtin middlewares that are easy to configure and use.
See :doc:`the documentation regarding these </lib/usage/middleware/builtin-middleware>` for more details.

.. seealso::

   If you're coming from Starlette / FastAPI, take a look at the
   :ref:`section on middleware <lib/migration/fastapi:Middleware>` in the migration guide.


.. toctree::
    :titlesonly:

    using-middleware
    builtin-middleware
    creating-middleware
