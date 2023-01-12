====================
Layered Architecture
====================

Starlite has a layered architecture comprising of (generally speaking) four layers:

#. The application object
#.  Routers
#.  Controllers
#. Handlers

There are many parameters that can be defined on every layer. And only that parameter
defined **closest to the handler** takes precedence. This allows for maximum flexibility
& simplicity when configuring complex applications. This also enables transparent
overriding of parameters.

That said, following is a list of parameters supported by the layered architecture:

.. TODO: Hyperlink these resources when their documentations are up & online.

* ``after_request``
* ``after_response``
* ``before_request``
* ``cache_control``
* ``dependencies``
* ``etag``
* ``exceptional_handlers``
* ``guards``
* ``middleware``
* ``opt``
* ``response_class``
* ``response_cookies``
* ``response_headers``
* ``security``
* ``tags``
* ``type_encoders``
