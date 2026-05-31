从 Flask 迁移
==============

ASGI 与 WSGI
~~~~~~~~~~~~

`Flask <https://flask.palletsprojects.com>`_ 是一个 WSGI 框架，而 Litestar 是使用现代 `ASGI <https://asgi.readthedocs.io>`_ 标准构建的。一个关键区别是 *ASGI* 是为异步而构建的。

虽然 Flask 增加了对 ``async/await`` 的支持，但其核心仍然是同步的；Flask 中的异步支持仅限于单个端点。这意味着虽然您可以在 Flask 中使用 ``async def`` 定义端点，**但它们不会并发运行** - 请求仍将一次处理一个。Flask 通过为每个请求创建一个事件循环来处理异步端点，在其中运行端点函数，然后返回其结果。

另一方面，ASGI 则完全相反；它在一个中央事件循环中运行所有内容。然后，Litestar 通过在非阻塞方式下 *在事件循环上* 运行同步函数来增加对同步函数的支持。这意味着同步和异步代码都可以并发运行。

路由
~~~~~~~

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

        .. code-block:: python

            from litestar import Litestar, get


            @get("/")
            def index() -> str:
                return "Index Page"


            @get("/hello")
            def hello() -> str:
                return "Hello, World"


            app = Litestar([index, hello])


路径参数
^^^^^^^^^^^^^^^

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

        .. code-block:: python

            from litestar import Litestar, get
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


            app = Litestar([show_user_profile, show_post, show_subpath])


..  seealso::

    要了解有关路径参数的更多信息，请查看文档中的此章节：

    * :doc:`/usage/routing/parameters`

请求对象
~~~~~~~~~~~~~~

在 Flask 中，当前请求可以通过全局 ``request`` 变量访问。在 Litestar 中，可以通过处理器函数中的可选参数访问请求。

.. tab-set::

    .. tab-item:: Flask
        :sync: flask

        .. code-block:: python

            from flask import Flask, request


            app = Flask(__name__)


            @app.get("/")
            def index():
                print(request.method)



    .. tab-item:: Litestar
        :sync: litestar

        .. code-block:: python

            from litestar import Litestar, get, Request


            @get("/")
            def index(request: Request) -> None:
                print(request.method)


请求方法
^^^^^^^^^^^^^^^

+---------------------------------+-------------------------------------------------------------------------------------------------------+
| Flask                           | Litestar                                                                                              |
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
| ``request.files``               | 使用 ``UploadFile`` 参见 :doc:`/usage/requests`                                                       |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.form``                | ``request.form()``，建议使用 ``Body`` 参见 :doc:`/usage/requests`                                     |
+---------------------------------+-------------------------------------------------------------------------------------------------------+
| ``request.get_json``            | ``request.json()``，建议使用 ``data`` 关键字参数，参见 :doc:`/usage/requests`                         |
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

    要了解有关请求的更多信息，请查看文档中的这些章节

    * :doc:`/usage/requests`
    * :doc:`/reference/connection`

静态文件
~~~~~~~~~~~~

与 Flask 一样，Litestar 也具有提供静态文件的功能，但虽然 Flask 会自动从 ``static`` 文件夹提供文件，但在 Litestar 中必须显式配置。

.. code-block:: python

   from litestar import Litestar
   from litestar.static_files import create_static_files_router

    app = Litestar(route_handlers=[
        create_static_files_router(path="/static", directories=["assets"]),
    ])

..  seealso::

    要了解有关静态文件的更多信息，请查看文档中的此章节

    * :doc:`/usage/static-files`

模板
~~~~~~~~~

Flask 内置了 `Jinja <https://jinja.palletsprojects.com/en/3.1.x/>`_ 模板引擎。您也可以在 Litestar 中使用 Jinja，但需要显式安装它。您可以通过使用 ``pip install 'litestar[jinja]'`` 安装 Litestar 来完成。除了 Jinja，Litestar 还支持 `Mako <https://www.makotemplates.org/>`_ 和 `Minijinja <https://github.com/mitsuhiko/minijinja/tree/main/minijinja-py>`_ 模板。

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

        .. code-block:: python

            from litestar import Litestar, get
            from litestar.contrib.jinja import JinjaTemplateEngine
            from litestar.response import Template
            from litestar.template.config import TemplateConfig


            @get("/hello/{name:str}")
            def hello(name: str) -> Template:
                return Template(response_name="hello.html", context={"name": name})


            app = Litestar(
                [hello],
                template_config=TemplateConfig(directory="templates", engine=JinjaTemplateEngine),
            )


..  seealso::
    要了解有关模板的更多信息，请查看文档中的此章节：

    * :doc:`/usage/templating`

设置 cookie 和标头
~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

        .. code-block:: python

            from litestar import Litestar, get, Response
            from litestar.datastructures import ResponseHeader, Cookie


            @get(
                "/static",
                response_headers={"my-header": ResponseHeader(value="header-value")},
                response_cookies=[Cookie("my-cookie", "cookie-value")],
            )
            def static() -> str:
                # 您可以在定义处理器时设置标头和 cookie
                ...


            @get("/dynamic")
            def dynamic() -> Response[str]:
                # 或者动态地，通过返回 Response 实例
                return Response(
                    "hello",
                    headers={"my-header": "header-value"},
                    cookies=[Cookie("my-cookie", "cookie-value")],
                )


..  seealso::
    要了解有关响应标头和 cookie 的更多信息，请查看文档中的这些章节：

    - :ref:`Responses - 设置响应标头 <usage/responses:setting response headers>`
    - :ref:`Responses - 设置响应 Cookie <usage/responses:setting response cookies>`

重定向
~~~~~~~~~

对于重定向，使用 ``Redirect`` 而不是 ``redirect``：

.. tab-set::

    .. tab-item:: Flask
        :sync: flask

        .. code-block:: python

            from flask import Flask, redirect, url_for


            app = Flask(__name__)


            @app.get("/")
            def index():
                return "hello"


            @app.get("/hello")
            def hello():
                return redirect(url_for("index"))



    .. tab-item:: Litestar
        :sync: litestar

        .. code-block:: python

            from litestar import Litestar, get
            from litestar.response import Redirect


            @get("/")
            def index() -> str:
                return "hello"


            @get("/hello")
            def hello() -> Redirect:
                return Redirect(path="/")


            app = Litestar([index, hello])


引发 HTTP 错误
~~~~~~~~~~~~~~~~~~~

使用 ``HTTPException`` 而不是 ``abort`` 函数：

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

        .. code-block:: python

            from litestar import Litestar, get
            from litestar.exceptions import HTTPException


            @get("/")
            def index() -> None:
                raise HTTPException(status_code=400, detail="this did not work")


            app = Litestar([index])


..  seealso::
    要了解有关异常的更多信息，请查看文档中的此章节：

    * :doc:`/usage/exceptions`

设置状态码
~~~~~~~~~~~~~~~~~~~~

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

        .. code-block:: python

            from litestar import Litestar, get, Response


            @get("/static", status_code=404)
            def static_status() -> str:
                return "not found"


            @get("/dynamic")
            def dynamic_status() -> Response[str]:
                return Response("not found", status_code=404)


            app = Litestar([static_status, dynamic_status])


序列化
~~~~~~~~~~~~~

Flask 使用显式转换（如 ``jsonify``）和推断（即返回数据的类型）的混合来确定数据应如何序列化。相反，Litestar 假设返回的数据旨在序列化为 JSON，并将这样做，除非另有说明。

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
                return "hello, world!"


            @app.get("/html")
            def get_html():
                return Response("<strong>hello, world</strong>", mimetype="text/html")



    .. tab-item:: Litestar
        :sync: litestar

        .. code-block:: python

            from litestar import Litestar, get, MediaType


            @get("/json")
            def get_json() -> dict[str, str]:
                return {"hello": "world"}


            @get("/text", media_type=MediaType.TEXT)
            def get_text() -> str:
                return "hello, world"


            @get("/html", media_type=MediaType.HTML)
            def get_html() -> str:
                return "<strong>hello, world</strong>"


            app = Litestar([get_json, get_text, get_html])


错误处理
~~~~~~~~~~~~~~

.. tab-set::

    .. tab-item:: Flask
        :sync: flask

        .. code-block:: python

            from flask import Flask
            from werkzeug.exceptions import HTTPException


            app = Flask(__name__)


            @app.errorhandler(HTTPException)
            def handle_exception(e): ...



    .. tab-item:: Litestar
        :sync: litestar

        .. code-block:: python

            from litestar import Litestar, Request, Response
            from litestar.exceptions import HTTPException


            def handle_exception(request: Request, exception: Exception) -> Response: ...


            app = Litestar([], exception_handlers={HTTPException: handle_exception})


..  seealso::

    要了解有关异常处理的更多信息，请查看文档中的此章节：

    * :ref:`usage/exceptions:exception handling`
