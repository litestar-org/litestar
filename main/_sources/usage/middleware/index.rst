Middleware
==========

Middlewares in Litestar are ASGI apps that are called "in the middle" between the application entrypoint and the
route handler function.

Litestar ships with several builtin middlewares that are easy to configure and use.
See :doc:`the documentation regarding these </usage/middleware/builtin-middleware>` for more details.

.. seealso::

    If you're coming from Starlette / FastAPI, take a look at the migration guide:

    * :ref:`Migration - FastAPI/Starlette - Middlewares <migration/fastapi:Middleware>`


.. toctree::
    :titlesonly:

    using-middleware
    builtin-middleware
    creating-middleware
