Layered Architecture
====================

.. TODO: Elaborate this section and reorganise the hyperlinks to the rest of the docs.

Every Starlite application comprises of four architectural layers:

#. The application layer
#. Routers
#. Controllers
#. Handlers

And each of those layers can accept certain parameters and in which case the parameter defined on the layer **closest to
the handler** takes precedence. This allows for maximum flexibility and simplicity when configuring complex
applications to enable transparent overriding of parameters.

The parameters which support layering are:

* :ref:`after_request <after_request>`
* :ref:`after_response <after_response>`
* :ref:`before_request <before_request>`
* :ref:`cache_control <lib/usage/responses:cache control>`
* :doc:`dependencies </lib/usage/dependency-injection>`
* :ref:`etag <lib/usage/responses:etag>`
* :doc:`exception_handlers </lib/usage/exceptions>`
* :doc:`guards </lib/usage/security/guards>`
* :doc:`middleware </lib/usage/middleware/index>`
* :ref:`opt <handler_opts>`
* :ref:`response_class <lib/usage/responses:custom responses>`
* :ref:`response_cookies <lib/usage/responses:response cookies>`
* :ref:`response_headers <lib/usage/responses:response headers>`
* ``security``
* ``tags``
* ``type_encoders``
