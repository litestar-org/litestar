Flask
=====

Layered configuration
---------------------

Litestar uses a layered architecture. The parts used to group routes can also be used
to hierarchically organize an application. Settings and configuration like dependencies,
exception handlers, guards, middleware, response cookies and headers, lifecycle hooks,
OpenAPI configuration and many more can be defined on any layer, and will be merged upon
registration.

The layers in hierarchical order are

1. Application (``Litestar``)
2. ``Router`` / ``Controller`` (these are on the same level and can be arbitrarily nested)
3. Handler (``BaseRouteHandler``)

When the same configuration is set on multiple layers, the value set closest to the
handler takes precedence.


Route handlers
--------------

Routes are declared with method-specific decorators
(:func:`~litestar.handlers.get`, :func:`~litestar.handlers.post`, ...) and registered on
an application, router or controller:

.. tab-set::

    .. tab-item:: Flask
        :sync: flask

        .. code-block:: python

            from flask import Flask

            app = Flask(__name__)

            @app.route("/")
            def index():
                return "Index Page"

            @app.route("/hello")
            def hello():
                return "Hello, World"

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/flask/routing.py
            :language: python

:class:`Routers <litestar.router.Router>` and
:class:`controllers <litestar.controller.Controller>` group handlers and bind them with
a shared set of configuration. They are part of Litestar's *layered architecture*.

.. seealso::

    * :ref:`Routing - Registering Routes <usage/routing/overview:registering routes>`


Path parameters
~~~~~~~~~~~~~~~

Flask declares converters inline: ``<int:post_id>``. Litestar calls these
"path parameters", which are declared like ``/post/{post_id:int}``. The handler can
request a path parameter by annotating a function parameter with
:data:`~litestar.params.FromPath`. By default, Litestar will try to inject a path
parameter matching the function parameter name, but you can also specify an alias
(see :ref:`usage/routing/parameters:aliasing`).

.. note::
    The type defined in the path parameter does not have to match the function
    parameter. The path parameter is what defines the input type, and what's reflected
    in the OpenAPI schema. The function parameter is what will be validated against.

.. tab-set::

    .. tab-item:: Flask
        :sync: flask

        .. code-block:: python

            from flask import Flask

            app = Flask(__name__)

            @app.route("/user/<username>")
            def show_user_profile(username):
                return f"User {username}"

            @app.route("/post/<int:post_id>")
            def show_post(post_id):
                return f"Post {post_id}"

            @app.route("/path/<path:subpath>")
            def show_subpath(subpath):
                return f"Subpath {subpath}"

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/flask/path_parameters.py
            :language: python

.. seealso::

    * :doc:`/usage/routing/parameters`


Sync and async handlers
~~~~~~~~~~~~~~~~~~~~~~~~

Both Flask and Litestar support synchronous and asynchronous functions, but they are
handled differently. Flask implements the `WSGI <https://peps.python.org/pep-3333/>`_
protocol, which is synchronous by nature, while Litestar implements
`ASGI <https://asgi.readthedocs.io>`_, an asynchronous protocol.

When Flask runs asynchronous endpoints, they run isolated from another. The handling of
requests is still synchronous. Litestar is asynchronous throughout, meaning one worker
can handle many asynchronous requests concurrently.

Litestar can also handle synchronous endpoints without blocking, by running them in a
thread pool. To enable this, set ``sync_to_thread=True`` on the handler decorator.

.. important::
    A sync handler without ``sync_to_thread`` set emits a runtime warning, since
    Litestar cannot tell whether the function blocks. Pass ``sync_to_thread=False`` to
    suppress the warning when the body genuinely does not block.

.. tab-set::

    .. tab-item:: Flask
        :sync: flask

        .. code-block:: python

            @app.get("/")
            def slow_handler():
                # blocking I/O on the worker
                time.sleep(1)
                return {"hello": "world"}

    .. tab-item:: Litestar
        :sync: litestar

        .. code-block:: python

            from litestar import get

            @get("/", sync_to_thread=True)
            def slow_handler() -> dict[str, str]:
                # blocking on a thread, event loop remains free
                time.sleep(1)
                return {"hello": "world"}


Lifespan
~~~~~~~~

Flask has ``@before_first_request`` for startup work and no matching hook for shutdown.
Litestar accepts one or more async context managers through
:paramref:`~litestar.app.Litestar.lifespan`; setup goes before the ``yield``, teardown
after.

.. literalinclude:: /examples/onboarding/flask/lifespan.py
    :language: python


Accessing the request
---------------------

Flask exposes the current request through ``flask.request``, a thread-local proxy. In
Litestar a handler that needs the request asks for it by name; the parameter is typed
as :class:`~litestar.connection.Request`.

.. tab-set::

    .. tab-item:: Flask
        :sync: flask

        .. code-block:: python

            from flask import Flask, request

            app = Flask(__name__)

            @app.get("/")
            def index():
                return {"method": request.method}

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/flask/request_object.py
            :language: python


Request attribute reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The table maps each ``flask.Request`` attribute to its Litestar counterpart

+---------------------------------+------------------------------------------------------------------------------------------------------------+
| Flask                           | Litestar                                                                                                   |
+=================================+============================================================================================================+
| ``request.args``                | Injected via function parameters marked with ``FromQuery``. Direct access through ``request.query_params`` |
+---------------------------------+------------------------------------------------------------------------------------------------------------+
| ``request.base_url``            | ``request.base_url``                                                                                       |
+---------------------------------+------------------------------------------------------------------------------------------------------------+
| ``request.authorization``       | ``request.auth``                                                                                           |
+---------------------------------+------------------------------------------------------------------------------------------------------------+
| ``request.cache_control``       | ``request.headers.get("cache-control")``                                                                   |
+---------------------------------+------------------------------------------------------------------------------------------------------------+
| ``request.content_encoding``    | ``request.headers.get("content-encoding")``                                                                |
+---------------------------------+------------------------------------------------------------------------------------------------------------+
| ``request.content_length``      | ``request.headers.get("content-length")``                                                                  |
+---------------------------------+------------------------------------------------------------------------------------------------------------+
| ``request.content_type``        | ``request.content_type``                                                                                   |
+---------------------------------+------------------------------------------------------------------------------------------------------------+
| ``request.cookies``             | ``request.cookies``                                                                                        |
+---------------------------------+------------------------------------------------------------------------------------------------------------+
| ``request.data``                | ``await request.body()``                                                                                   |
+---------------------------------+------------------------------------------------------------------------------------------------------------+
| ``request.date``                | ``request.headers.get("date")``                                                                            |
+---------------------------------+------------------------------------------------------------------------------------------------------------+
| ``request.endpoint``            | ``request.route_handler.name``                                                                             |
+---------------------------------+------------------------------------------------------------------------------------------------------------+
| ``request.environ``             | ``request.scope``                                                                                          |
+---------------------------------+------------------------------------------------------------------------------------------------------------+
| ``request.files``               | Injected via :class:`~litestar.datastructures.UploadFile`; see :ref:`usage/requests:Content-type`          |
+---------------------------------+------------------------------------------------------------------------------------------------------------+
| ``request.form``                | Injected via the ``data`` parameter, marked with ``Body``, see :ref:`usage/requests:Content-type`          |
+---------------------------------+------------------------------------------------------------------------------------------------------------+
| ``request.get_json``            | Injected via the ``data`` parameter                                                                        |
+---------------------------------+------------------------------------------------------------------------------------------------------------+
| ``request.headers``             | ``request.headers``                                                                                        |
+---------------------------------+------------------------------------------------------------------------------------------------------------+
| ``request.host``                | :octicon:`dash`                                                                                            |
+---------------------------------+------------------------------------------------------------------------------------------------------------+
| ``request.if_match``            | ``request.headers.get("if-match")``                                                                        |
+---------------------------------+------------------------------------------------------------------------------------------------------------+
| ``request.if_modified_since``   | ``request.headers.get("if-modified-since")``                                                               |
+---------------------------------+------------------------------------------------------------------------------------------------------------+
| ``request.if_none_match``       | ``request.headers.get("if-none-match")``                                                                   |
+---------------------------------+------------------------------------------------------------------------------------------------------------+
| ``request.if_range``            | ``request.headers.get("if-range")``                                                                        |
+---------------------------------+------------------------------------------------------------------------------------------------------------+
| ``request.if_unmodified_since`` | ``request.headers.get("if-unmodified-since")``                                                             |
+---------------------------------+------------------------------------------------------------------------------------------------------------+
| ``request.method``              | ``request.method``                                                                                         |
+---------------------------------+------------------------------------------------------------------------------------------------------------+
| ``request.path``                | ``request.scope["path"]``                                                                                  |
+---------------------------------+------------------------------------------------------------------------------------------------------------+
| ``request.query_string``        | ``request.scope["query_string"]``                                                                          |
+---------------------------------+------------------------------------------------------------------------------------------------------------+
| ``request.range``               | ``request.headers.get("range")``                                                                           |
+---------------------------------+------------------------------------------------------------------------------------------------------------+
| ``request.referer``             | ``request.headers.get("referer")``                                                                         |
+---------------------------------+------------------------------------------------------------------------------------------------------------+
| ``request.remote_addr``         | ``request.client.host``  / ``request.client.port``                                                         |
+---------------------------------+------------------------------------------------------------------------------------------------------------+
| ``request.root_path``           | ``request.scope["root_path"]``                                                                             |
+---------------------------------+------------------------------------------------------------------------------------------------------------+
| ``request.server``              | ``request.scope["server"]``                                                                                |
+---------------------------------+------------------------------------------------------------------------------------------------------------+
| ``request.url``                 | ``request.url``                                                                                            |
+---------------------------------+------------------------------------------------------------------------------------------------------------+
| ``request.user_agent``          | ``request.headers.get("user-agent")``                                                                      |
+---------------------------------+------------------------------------------------------------------------------------------------------------+

.. seealso::

    * :doc:`/usage/requests`
    * :doc:`/reference/connection`


Per-request state
~~~~~~~~~~~~~~~~~

Flask uses ``flask.g`` for values that should live for the duration of a single request.
Litestar uses ``request.state``, a mutable mapping attached to the request.

.. tab-set::

    .. tab-item:: Flask
        :sync: flask

        .. code-block:: python

            from flask import Flask, g, request

            app = Flask(__name__)

            @app.before_request
            def set_user() -> None:
                g.user = request.headers.get("x-user", "anonymous")

            @app.get("/")
            def index():
                return {"user": g.user}

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/flask/request_state.py
            :language: python


The current application
~~~~~~~~~~~~~~~~~~~~~~~

``flask.current_app`` is a thread-local proxy. Litestar exposes the application as
``request.app``, or as an ``app`` parameter on lifecycle hooks and middleware factories.


File uploads
~~~~~~~~~~~~

Flask exposes uploaded files through ``request.files``. Litestar binds them to a
``data`` parameter typed as :class:`~litestar.datastructures.UploadFile` (or a list of
them), with ``media_type`` set to
:class:`RequestEncodingType.URL_ENCODED <litestar.enums.RequestEncodingType>` or
:class:`RequestEncodingType.MULTI_PART <litestar.enums.RequestEncodingType>`

.. tab-set::

    .. tab-item:: Flask
        :sync: flask

        .. code-block:: python

            from flask import Flask, request

            app = Flask(__name__)

            @app.post("/upload")
            def upload():
                f = request.files["data"]
                return {"filename": f.filename}

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/flask/file_uploads.py
            :language: python


Producing responses
-------------------

Status codes
~~~~~~~~~~~~

Flask overrides the default ``200`` by returning a ``(body, status)`` tuple. Litestar
declares the status code on the decorator with ``status_code=`` when it is fixed for the
handler, and on the :class:`~litestar.response.Response` instance when it depends on the
request.

Litestar picks the status code from the HTTP method by default: ``POST`` defaults to
``201 Created``, ``DELETE`` to ``204 No Content``, everything else to ``200 OK``.

.. tab-set::

    .. tab-item:: Flask
        :sync: flask

        .. code-block:: python

            from flask import Flask

            app = Flask(__name__)

            @app.get("/")
            def index():
                return "not found", 404

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/flask/status_codes.py
            :language: python


Cookies and headers
~~~~~~~~~~~~~~~~~~~

Flask builds a response with ``make_response`` and mutates it. Litestar offers two
paths: declare static values on the decorator with ``response_cookies`` and
``response_headers``, or return a :class:`~litestar.response.Response` with ``cookies=``
and ``headers=`` when the values depend on the request.

.. tab-set::

    .. tab-item:: Flask
        :sync: flask

        .. code-block:: python

            from flask import Flask, make_response

            app = Flask(__name__)

            @app.get("/")
            def index():
                response = make_response("hello")
                response.set_cookie("my-cookie", "cookie-value")
                response.headers["my-header"] = "header-value"
                return response

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/flask/cookies_and_headers.py
            :language: python

.. seealso::

    * :ref:`Responses - Setting Response Headers <usage/responses/headers_and_cookies:Setting Response Headers>`
    * :ref:`Responses - Setting Response Cookies <usage/responses/headers_and_cookies:Setting Response Cookies>`


Serialization
~~~~~~~~~~~~~

Flask mixes explicit ``jsonify`` calls with inference from the return value.
Litestar infers content encoding type from a handler's return annotation. Structured
types (``dict``, ``list``, dataclasses, Pydantic models, msgspec ``Struct``\ s, attrs
classes, :class:`typing.TypedDict`, etc.) default to JSON, ``str`` returns
``text/plain``. You can set a ``media_type=`` on the handler decorator to override these
defaults.

.. tab-set::

    .. tab-item:: Flask
        :sync: flask

        .. code-block:: python

            from flask import Flask, Response

            app = Flask(__name__)

            @app.get("/json")
            def get_json():
                return {"hello": "world"}

            @app.get("/text")
            def get_text():
                return "hello, world"

            @app.get("/html")
            def get_html():
                return Response("<strong>hello, world</strong>", mimetype="text/html")

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/flask/serialization.py
            :language: python


.. seealso::
    :ref:`usage/responses/media_types_and_status_codes:Media Type`



URL lookup
~~~~~~~~~~

Flask exposes ``url_for(endpoint, **params)`` as a module-level function.
Litestar exposes :meth:`request.url_for <litestar.connection.ASGIConnection.url_for>` on
the request instead. The endpoint name comes from an explicit ``name=`` keyword on the
handler decorator, the equivalent of Flask's view-function name.

.. tab-set::

    .. tab-item:: Flask
        :sync: flask

        .. code-block:: python

            from flask import url_for

            url_for("index")

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/flask/url_for.py
            :language: python


Templates
~~~~~~~~~

Flask ships Jinja2 and renders templates with ``render_template``. Litestar treats
templating as opt-in: Jinja2 is available through the ``litestar[jinja]`` extra, Mako
through ``litestar[mako]``. The engine is configured on the application through
:class:`~litestar.template.config.TemplateConfig`, and each handler returns a
:class:`~litestar.response.Template` — the equivalent of ``render_template``'s return
value.

.. tab-set::

    .. tab-item:: Flask
        :sync: flask

        .. code-block:: python

            from flask import Flask, render_template

            app = Flask(__name__)

            @app.route("/hello/<name>")
            def hello(name):
                return render_template("hello.html", name=name)

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/flask/templates.py
            :language: python

.. seealso::

    * :doc:`/usage/templating`


Streaming responses
~~~~~~~~~~~~~~~~~~~

Flask streams by returning a generator wrapped in ``flask.Response``. In Litestar, you
can return a :class:`~litestar.response.Stream` built from a sync or async iterator.

.. tab-set::

    .. tab-item:: Flask
        :sync: flask

        .. code-block:: python

            from flask import Flask, Response

            app = Flask(__name__)

            @app.get("/stream")
            def stream():
                def gen():
                    for i in range(3):
                        yield f"data: {i}\n\n"

                return Response(gen(), mimetype="text/event-stream")

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/flask/streaming.py
            :language: python


Exceptions and error responses
------------------------------

Flask aborts with ``abort(code, description)``. Litestar raises an
:class:`~litestar.exceptions.HTTPException` (or a subclass) directly.

.. tab-set::

    .. tab-item:: Flask
        :sync: flask

        .. code-block:: python

            from flask import Flask, abort

            app = Flask(__name__)

            @app.get("/")
            def index():
                abort(400, "this did not work")

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/flask/http_errors.py
            :language: python

.. seealso::

    * :doc:`/usage/exceptions`


Custom exception handlers
~~~~~~~~~~~~~~~~~~~~~~~~~

Flask registers handlers through ``@app.errorhandler``. Litestar accepts a mapping from
an exception class or status code to a handler callable.

.. tip::
    Exception handling is part of Litestar's layered architecture, so these
    can be declared on applications, routers, controllers or route handlers.

.. tab-set::

    .. tab-item:: Flask
        :sync: flask

        .. code-block:: python

            from flask import Flask
            from werkzeug.exceptions import HTTPException

            app = Flask(__name__)

            @app.errorhandler(HTTPException)
            def handle_exception(e):
                return {"detail": e.description}, e.code

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/flask/exception_handlers.py
            :language: python

.. seealso::

    * :ref:`usage/exceptions:exception handling`


Before and after request hooks
------------------------------

Flask uses ``@app.before_request`` and ``@app.after_request``. Litestar accepts the same
callables through the ``before_request`` and ``after_request`` keyword arguments on any
layer.

.. tip::
    Lifecycle hooks are part of Litestar's layered architecture, so these
    can be declared on applications, routers, controllers or route handlers

.. tab-set::

    .. tab-item:: Flask
        :sync: flask

        .. code-block:: python

            from flask import Flask, g, request

            app = Flask(__name__)

            @app.before_request
            def attach_user() -> None:
                g.user = "alice"

            @app.after_request
            def wrap_text(response):
                if response.mimetype == "text/plain":
                    return {"value": response.get_data(as_text=True)}
                return response

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/flask/before_after_hooks.py
            :language: python

.. seealso::

    * :doc:`/usage/lifecycle-hooks`


Sessions
--------

Flask exposes ``flask.session`` as a thread-local dictionary backed by a signed cookie.
Litestar provides sessions via a session middleware, and exposes ``request.session`` as
a mutable mapping. Two backends are available:
:class:`~litestar.middleware.session.server_side.ServerSideSessionConfig` keeps the data
on the server and a session id in the cookie;
:class:`~litestar.middleware.session.client_side.CookieBackendConfig`
stores encrypted data in the cookie itself (closest to Flask's default).

.. tab-set::

    .. tab-item:: Flask
        :sync: flask

        .. code-block:: python

            from flask import Flask, session

            app = Flask(__name__)
            app.secret_key = "..."

            @app.post("/login")
            def login():
                session["user"] = "alice"
                return ""

            @app.get("/whoami")
            def whoami():
                return {"user": session.get("user")}

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/flask/sessions.py
            :language: python

.. seealso::

    * :doc:`/usage/middleware/builtin-middleware`


Static files
------------

Flask serves files from a folder named ``static`` automatically. Litestar offers an
equivalent in :func:`~litestar.static_files.create_static_files_router`, which can be
registered to serve files from a configured directory:

.. literalinclude:: /examples/onboarding/flask/static_files.py
    :language: python

.. seealso::

    * :doc:`/usage/static-files`


WebSockets
----------

Flask does not include WebSocket support natively, but `flask-sock`` and
``flask-socketio`` are popular extensions from the ecosystem. Litestar does include
native WebSocket support, coming in three different shapes:

- :func:`~litestar.handlers.websocket`: direct connection handling via raw `ASGI WebSockets <https://asgi.readthedocs.io/en/latest/specs/www.html#websocket>`_
- :func:`~litestar.handlers.websocket_listener`: Per-message callback style that takes
  and returns typed values; the framework handles accept, the receive loop, and
  serialisation.
- :func:`~litestar.handlers.websocket_stream`: Async generator to produce messages that
  are pushed to the WebSocket;  the framework handles accept, the receive loop, and
  serialisation.

.. literalinclude:: /examples/onboarding/flask/websockets.py
    :language: python

For broadcast and pub/sub patterns, pair these handlers with the
:doc:`channels </usage/channels>` plugin. Channels handles per-channel subscriptions,
history, and inter-process fan-out through a pluggable broker, and can generate
WebSocket route handlers that publish incoming events to subscribed clients.

.. seealso::

    * :doc:`/usage/websockets`


Testing
-------

Flask exposes ``app.test_client()``. Litestar offers
:class:`~litestar.testing.TestClient` (which wraps an existing app) and
:func:`~litestar.testing.create_test_client` (which builds a fresh app from the same
options as :class:`~litestar.app.Litestar`).

.. tab-set::

    .. tab-item:: Flask
        :sync: flask

        .. code-block:: python

            def test_index() -> None:
                client = app.test_client()
                response = client.get("/")
                assert response.status_code == 200
                assert response.text == "Index Page"

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/flask/test_handler.py
            :language: python

.. seealso::

    * :doc:`/usage/testing`


Further reading
---------------

These are not the only differences between Flask and Litestar, so if you want to keep
reading about features, here's a select list:

- :doc:`/usage/openapi/index`
- :doc:`/usage/dependency-injection`
- :doc:`/usage/plugins/index`
- :doc:`/usage/middleware/index`


.. _flask-migration-quick-reference:

Quick reference
---------------

A lookup table for the most common translations.

+--------------------------------+--------------------------------------+------------------------------------------+
| Concept                        | Flask                                | Litestar                                 |
+================================+======================================+==========================================+
| Route declaration              | ``@app.route("/")``                  | ``@get("/")`` + ``Litestar([handler])``  |
+--------------------------------+--------------------------------------+------------------------------------------+
| Path parameter                 | ``/items/<int:id>``                  | ``/items/{id:int}`` + ``FromPath[int]``  |
+--------------------------------+--------------------------------------+------------------------------------------+
| Request access                 | global ``request``                   | ``request: Request`` parameter           |
+--------------------------------+--------------------------------------+------------------------------------------+
| Request-scoped state           | ``flask.g``                          | ``request.state``                        |
+--------------------------------+--------------------------------------+------------------------------------------+
| Current application            | ``flask.current_app``                | ``request.app``                          |
+--------------------------------+--------------------------------------+------------------------------------------+
| Static files                   | automatic ``static/``                | ``create_static_files_router``           |
+--------------------------------+--------------------------------------+------------------------------------------+
| Templates                      | ``render_template``                  | ``Template()`` + ``TemplateConfig``      |
+--------------------------------+--------------------------------------+------------------------------------------+
| Cookies / headers              | ``make_response`` + ``.set_cookie``  | ``response_cookies=`` / ``Response(...)``|
+--------------------------------+--------------------------------------+------------------------------------------+
| Redirect                       | ``redirect`` + ``url_for``           | ``Redirect`` + ``request.url_for``       |
+--------------------------------+--------------------------------------+------------------------------------------+
| URL generation                 | ``url_for``                          | ``request.url_for(handler_name)``        |
+--------------------------------+--------------------------------------+------------------------------------------+
| HTTPException                  | ``abort(400, ...)``                  | ``HTTPException(status_code=400, ...)``  |
+--------------------------------+--------------------------------------+------------------------------------------+
| Status code                    | ``return body, status``              | ``status_code=`` / ``Response(...)``     |
+--------------------------------+--------------------------------------+------------------------------------------+
| Serialization                  | ``jsonify`` / inference              | return type annotation                   |
+--------------------------------+--------------------------------------+------------------------------------------+
| Exception handler              | ``@app.errorhandler``                | ``exception_handlers={Exc: handler}``    |
+--------------------------------+--------------------------------------+------------------------------------------+
| Before/after request           | ``@before_request`` / ``@after_*``   | ``before_request=`` / ``after_request=`` |
+--------------------------------+--------------------------------------+------------------------------------------+
| Sessions                       | ``flask.session``                    | ``ServerSideSessionConfig``              |
+--------------------------------+--------------------------------------+------------------------------------------+
| File upload                    | ``request.files``                    | ``UploadFile`` + ``Body(MULTI_PART)``    |
+--------------------------------+--------------------------------------+------------------------------------------+
| Streaming response             | ``Response(generator, ...)``         | ``Stream(iterator)``                     |
+--------------------------------+--------------------------------------+------------------------------------------+
| WebSocket                      | not built-in                         | ``@websocket("/ws")``                    |
+--------------------------------+--------------------------------------+------------------------------------------+
| Lifespan                       | ``@before_first_request``            | ``lifespan=[ctx_mgr]``                   |
+--------------------------------+--------------------------------------+------------------------------------------+
| Test client                    | ``app.test_client()``                | ``TestClient`` / ``create_test_client``  |
+--------------------------------+--------------------------------------+------------------------------------------+
