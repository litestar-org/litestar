From Flask
----------

ASGI vs WSGI
~~~~~~~~~~~~

`Flask <https://flask.palletsprojects.com>`_ is a WSGI framework, whereas Starlite
is built using the modern `ASGI <https://asgi.readthedocs.io>`_ standard. A key difference
is that *ASGI* is built with async in mind.

While Flask has added support for ``async/await``, it remains synchronous at its core;
The async support in Flask is limited to individual endpoints.
What this means is that while you can use ``async def`` to define endpoints in Flask,
**they will not run concurrently** - requests will still be processed one at a time.
Flask handles asynchronous endpoints by creating an event loop for each request, run the
endpoint function in it and then return its result.

ASGI on the other hand does the exact opposite; It runs everything in a central event loop.
Starlite then adds support for synchronous functions by running them in a non-blocking way
*on the event loop*. What this means is that synchronous and asynchronous code both run
concurrently.

Routing
~~~~~~~

.. tab-set::

    .. tab-item:: Flask
        :sync: flask

        .. code-block:: python

            from flask import Flask


            app = Flask(_name_)


            @app.route("/")
            def index():
                return "Index Page"


            @app.route("/hello")
            def hello():
                return "Hello, World"


    .. tab-item:: Starlite
        :sync: starlite

        .. code-block:: python

            from starlite import Starlite, get


            @get("/")
            def index() -> str:
                return "Index Page"


            @get("/hello")
            def hello() -> str:
                return "Hello, World"


            app = Starlite([index, hello])


Path parameters
^^^^^^^^^^^^^^^

.. tab-set::
    .. tab-item:: Flask
        :sync: flask

        .. code-block:: python

            from flask import Flask


            app = Flask(_name_)


            @app.route("/user/<username>")
            def show_user_profile(username):
                return f"User {username}"


            @app.route("/post/<int:post_id>")
            def show_post(post_id):
                return f"Post {post_id}"


            @app.route("/path/<path:subpath>")
            def show_subpath(subpath):
                return f"Subpath {subpath}"



    .. tab-item:: Starlite
        :sync: starlite

        .. code-block:: python

            from starlite import Starlite, get
            from pathlib import Path


            @get("/user/{username:str}")
            def show_user_profile(username: str) -> str:
                return f"User {username}"


            @get("/post/{post_id:int}")
            def show_post(post_id: int) -> str:
                return f"Post {post_id}"


            @get("/path/{subpath:path}")
            def show_subpath(subpath: Path) -> str:
                return f"Subpath {subpath}"


            app = Starlite([show_user_profile, show_post, show_subpath])


..  seealso::

    To learn more about path parameters, check out this chapter
    in the documentation: `Path parameters <usage/3-parameters/0-path-parameters/>`_

Request object
~~~~~~~~~~~~~~

In Flask, the current request can be accessed through a global ``request`` variable. In Starlite,
the request can be accessed through an optional parameter in the handler function.

.. tab-set::

    .. tab-item:: Flask
        :sync: flask

        .. code-block:: python

            from flask import Flask, request


            app = Flask(_name_)


            @app.get("/")
            def index():
                print(request.method)



    .. tab-item:: Starlite
        :sync: starlite

        .. code-block:: python

            from starlite import Starlite, get, Request


            @get("/")
            def index(request: Request) -> None:
                print(request.method)


Request methods
^^^^^^^^^^^^^^^

+---------------------------------+-------------------------------------------------------------------------------------------------------+
| Flask                           | Starlite                                                                                              |
+=================================+=======================================================================================================+
| ``request.args``                | ``request.query_params``                                                                              |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.base_url``            | ``request.base_url``                                                                                  |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.authorization``       | ``request.auth``                                                                                      |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.cache_control``       | ``request.headers.get("cache-control")``                                                              |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.content_encoding``    | ``request.headers.get("content-encoding")``                                                           |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.content_length``      | ``request.headers.get("content-length")``                                                             |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.content_md5``         | :octicon:`dash`                                                                                       |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.content_type``        | ``request.content_type``                                                                              |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.cookies``             | ``request.cookies``                                                                                   |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.data``                | ``request.body()``                                                                                    |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.date``                | ``request.headers.get("date")``                                                                       |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.endpoint``            | ``request.route_handler``                                                                             |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.environ``             | ``request.scope``                                                                                     |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.files``               | Use ```UploadFile`` <usage/4-request-data/#file-uploads>`__                                           |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.form``                | ``request.form()``, prefer ```Body`` <usage/4-request-data/#specifying-a-content-type>`__             |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.get_json``            | ``request.json()``, prefer the ```data keyword argument`` <usage/4-request-data/#request-body>`__     |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.headers``             | ``request.headers``                                                                                   |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.host``                | :octicon:`dash`                                                                                       |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.host_url``            | :octicon:`dash`                                                                                       |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.if_match``            | ``request.headers.get("if-match")``                                                                   |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.if_modified_since``   | ``request.headers.get("if_modified_since")``                                                          |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.if_none_match``       | ``request.headers.get("if_none_match")``                                                              |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.if_range``            | ``request.headers.get("if_range")``                                                                   |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.if_unmodified_since`` | ``request.headers.get("if_unmodified_since")``                                                        |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.method``              | ``request.method``                                                                                    |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.mimetype``            | :octicon:`dash`                                                                                       |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.mimetype_params``     | :octicon:`dash`                                                                                       |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.origin``              | :octicon:`dash`                                                                                       |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.path``                | ``request.scope["path"]``                                                                             |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.query_string``        | ``request.scope["query_string"]``                                                                     |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.range``               | ``request.headers.get("range")``                                                                      |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.referrer``            | ``request.headers.get("referrer")``                                                                   |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.remote_addr``         | :octicon:`dash`                                                                                       |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.remote_user``         | :octicon:`dash`                                                                                       |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.root_path``           | ``request.scope["root_path"]``                                                                        |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.server``              | ``request.scope["server"]``                                                                           |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.stream``              | ``request.stream``                                                                                    |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.url``                 | ``request.url``                                                                                       |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.url_charset``         | :octicon:`dash`                                                                                       |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.user_agent``          | ``request.headers.get("user-agent")``                                                                 |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.user_agent``          | ``request.headers.get("user-agent")``                                                                 |
+---------------------------------+-------------------------------------------------------------------------------------------------------+

..  seealso::

    To learn more about requests,, check out these chapters in the documentation

    * :doc:`/usage/request-data`
    * :doc:`/reference/connection/index`

Static files
~~~~~~~~~~~~

Like Flask, Starlite also has capabilities for serving static files, but while Flask
will automatically serve files from a ``static`` folder, this has to be configured explicitly
in Starlite.

.. code-block:: python

   from starlite import Starlite, StaticFilesConfig

   app = Starlite(
       [], static_files_config=StaticFilesConfig(path="/static", directories=["static"])
   )

..  seealso::

    To learn more about static files, check out this chapter in the documentation:
    `Static files <usage/0-the-starlite-app/3-static-files/>`_

Templates
~~~~~~~~~

Flask comes with the `Jinja <https://jinja.palletsprojects.com/en/3.1.x/>`_ templating
engine built-in. You can use Jinja with Starlite as well, but you’ll need to install it
explicitly. You can do by installing Starlite with ``pip install starlite[jinja]``.
In addition to Jinja, Starlite supports `Mako <https://www.makotemplates.org/>`_ templates as well.

.. tab-set::
    .. tab-item:: Flask
        :sync: flask

        .. code-block:: python

            from flask import Flask, render_template


            app = Flask(_name_)


            @app.route("/hello/<name>")
            def hello(name):
                return render_template("hello.html", name=name)



    .. tab-item:: Starlite
        :sync: starlite

        .. code-block:: python

            from starlite import Starlite, get, TemplateConfig, Template
            from starlite.contrib.jinja import JinjaTemplateEngine


            @get("/hello/{name:str}")
            def hello(name: str) -> Template:
                return Template(name="hello.html", context={"name": name})


            app = Starlite(
                [hello],
                template_config=TemplateConfig(directory="templates", engine=JinjaTemplateEngine),
            )


..  seealso::
    To learn more about templates, check out this chapter in the documentation:
    `Template engines <usage/16-templating/0-template-engines/>`_

Setting cookies and headers
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. tab-set::

    .. tab-item:: Flask
        :sync: flask

        .. code-block:: python

            from flask import Flask, make_response

            app = Flask(_name_)


            @app.get("/")
            def index():
                response = make_response("hello")
                response.set_cookie("my-cookie", "cookie-value")
                response.headers["my-header"] = "header-value"
                return response



    .. tab-item:: Starlite
        :sync: starlite

        .. code-block:: python

            from starlite import Starlite, get, ResponseHeader, Cookie, Response


            @get(
                "/static",
                response_headers={"my-header": ResponseHeader(value="header-value")},
                response_cookies=[Cookie("my-cookie", "cookie-value")],
            )
            def static() -> str:
                # you can set headers and cookies when defining handlers
                ...


            @get("/dynamic")
            def dynamic() -> Response[str]:
                # or dynamically, by returning an instance of Response
                return Response(
                    "hello",
                    headers={"my-header": "header-value"},
                    cookies=[Cookie("my-cookie", "cookie-value")],
                )


..  seealso::
    To learn more about response headers and cookies, check out these chapters in the
    documentation:

    - :ref:`Response headers <usage/responses:response headers>`
    - :ref:`Response cookies <usage/responses:response cookies>`

Redirects
~~~~~~~~~

For redirects, instead of ``redirect`` use ``Redirect``:

.. tab-set::

    .. tab-item:: Flask
        :sync: flask

        .. code-block:: python

            from flask import Flask, redirect, url_for

            app = Flask(_name_)


            @app.get("/")
            def index():
                return "hello"


            @app.get("/hello")
            def hello():
                return redirect(url_for("index"))



    .. tab-item:: Starlite
        :sync: starlite

        .. code-block:: python

            from starlite import Starlite, get, Redirect


            @get("/")
            def index() -> str:
                return "hello"


            @get("/hello")
            def hello() -> Redirect:
                return Redirect(path="index")


            app = Starlite([index, hello])


Raising HTTP errors
~~~~~~~~~~~~~~~~~~~

Instead of using the ``abort`` function, raise an ``HTTPException``:

.. tab-set::

    .. tab-item:: Flask
        :sync: flask

        .. code-block:: python

            from flask import Flask, abort

            app = Flask(_name_)


            @app.get("/")
            def index():
                abort(400, "this did not work")



    .. tab-item:: Starlite
        :sync: starlite

        .. code-block:: python

            from starlite import Starlite, get, HTTPException


            @get("/")
            def index() -> None:
                raise HTTPException(status_code=400, detail="this did not work")


            app = Starlite([index])


..  seealso::
    To learn more about exceptions, check out this chapter in the documentation: `Exceptions <usage/17-exceptions>`_

Setting status codes
~~~~~~~~~~~~~~~~~~~~

.. tab-set::

    .. tab-item:: Flask
        :sync: flask

        .. code-block:: python

            from flask import Flask


            app = Flask(_name_)


            @app.get("/")
            def index():
                return "not found", 404



    .. tab-item:: Starlite
        :sync: starlite

        .. code-block:: python

            from starlite import Starlite, get, Response


            @get("/static", status_code=404)
            def static_status() -> str:
                return "not found"


            @get("/dynamic")
            def dynamic_status() -> Response[str]:
                return Response("not found", status_code=404)


            app = Starlite([static_status, dynamic_status])


Serialization
~~~~~~~~~~~~~

Flask uses a mix of explicit conversion (such as ``jsonify``) and inference (i.e. the type
of the returned data) to determine how data should be serialized. Starlite instead assumes
the data returned is intended to be serialized into JSON and will do so unless told otherwise.

.. tab-set::

    .. tab-item:: Flask
        :sync: flask

        .. code-block:: python

            from flask import Flask, Response

            app = Flask(_name_)


            @app.get("/json")
            def get_json():
                return {"hello": "world"}


            @app.get("/text")
            def get_text():
                return "hello, world!"


            @app.get("/html")
            def get_html():
                return Response("<strong>hello, world</strong>", mimetype="text/html")



    .. tab-item:: Starlite
        :sync: starlite

        .. code-block:: python

            from starlite import Starlite, get, MediaType


            @get("/json")
            def get_json() -> dict[str, str]:
                return {"hello": "world"}


            @get("/text", media_type=MediaType.TEXT)
            def get_text() -> str:
                return "hello, world"


            @get("/html", media_type=MediaType.HTML)
            def get_html() -> str:
                return "<strong>hello, world</strong>"


            app = Starlite([get_json, get_text, get_html])


Error handling
~~~~~~~~~~~~~~

.. tab-set::

    .. tab-item:: Flask
        :sync: flask

        .. code-block:: python

            from flask import Flask
            from werkzeug.exceptions import HTTPException


            app = Flask(_name_)


            @app.errorhandler(HTTPException)
            def handle_exception(e): ...



    .. tab-item:: Starlite
        :sync: starlite

        .. code-block:: python

            from starlite import Starlite, HTTPException, Request, Response


            def handle_exception(request: Request, exception: Exception) -> Response: ...


            app = Starlite([], exception_handlers={HTTPException: handle_exception})


..  seealso::

    To learn more about exception handling, check out this chapter in the documentation:
    `Exception handling <usage/17-exceptions/#exception-handling>`_
