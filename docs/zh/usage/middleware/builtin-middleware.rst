===============
内置中间件
===============

CORS
----

`CORS（跨域资源共享） <https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS>`_ 是一种常见的安全机制，
通常使用中间件实现。要在 Litestar 应用程序中启用 CORS，只需将 :class:`~litestar.config.cors.CORSConfig` 
的实例传递给 :class:`~litestar.app.Litestar`：

.. code-block:: python

   from litestar import Litestar
   from litestar.config.cors import CORSConfig

   cors_config = CORSConfig(allow_origins=["https://www.example.com"])

   app = Litestar(route_handlers=[...], cors_config=cors_config)


CSRF
----

`CSRF（跨站请求伪造） <https://owasp.org/www-community/attacks/csrf>`_ 是一种攻击类型，
其中从 Web 应用程序信任的用户提交未经授权的命令。此攻击通常使用社会工程技巧，
欺骗受害者点击包含恶意制作的未经授权请求的 URL。然后，用户的浏览器将此恶意制作的请求发送到目标 Web 应用程序。
如果用户在 Web 应用程序中处于活动会话中，应用程序将此新请求视为用户提交的授权请求。
因此，攻击者可以强制用户执行用户不打算执行的操作，例如：


.. code-block:: text

    POST /send-money HTTP/1.1
    Host: target.web.app
    Content-Type: application/x-www-form-urlencoded

    amount=1000usd&to=attacker@evil.com


此中间件通过执行以下操作来防止 CSRF 攻击：

1. 在第一个"安全"请求（例如 GET）上 - 使用服务器创建的特殊令牌设置 cookie
2. 在每个后续的"不安全"请求（例如 POST）上 - 确保请求包含具有此令牌的表单字段或附加标头（下面将详细介绍）

要在 Litestar 应用程序中启用 CSRF 保护，只需将 
:class:`~litestar.config.csrf.CSRFConfig` 的实例传递给 Litestar 构造函数：

.. code-block:: python

    from litestar import Litestar, get, post
    from litestar.config.csrf import CSRFConfig


    @get()
    async def get_resource() -> str:
        # GET 是安全方法之一
        return "some_resource"

    @post("{id:int}")
    async def create_resource(id: int) -> bool:
        # POST 是不安全方法之一
        return True

    csrf_config = CSRFConfig(secret="my-secret")

    app = Litestar([get_resource, create_resource], csrf_config=csrf_config)


以下代码片段演示如何将 cookie 名称更改为 ``"some-cookie-name"`` 并将标头名称更改为 ``"some-header-name"``。

.. code-block:: python

    csrf_config = CSRFConfig(secret="my-secret", cookie_name='some-cookie-name', header_name='some-header-name')


任何可以使用标头或表单数据键发出请求的客户端都可以访问受 CSRF 保护的路由。


.. note::

    表单数据键当前无法配置。它应该仅通过键 ``"_csrf_token"`` 传递

在 Python 中，可以使用任何客户端，如 `requests <https://github.com/psf/requests>`_ 或 `httpx <https://github.com/encode/httpx>`_。
建议使用客户端或会话，因为它们提供跨请求的 cookie 持久性。
以下是使用 `httpx.Client <https://www.python-httpx.org/api/#client>`_ 的示例。

.. code-block:: python

    import httpx


    with httpx.Client() as client:
        get_response = client.get("http://localhost:8000/")

        # "csrftoken" 是默认的 cookie 名称
        csrf = get_response.cookies["csrftoken"]

        # "x-csrftoken" 是默认的标头名称
        post_response_using_header = client.post("http://localhost:8000/1", headers={"x-csrftoken": csrf})
        assert post_response_using_header.status_code == 201

        # "_csrf_token" 是默认的*不可*配置的表单数据键
        post_response_using_form_data = client.post("http://localhost:8000/1", data={"_csrf_token": csrf})
        assert post_response_using_form_data.status_code == 201

        # 尽管传递了标头，此请求将失败，因为它的会话中没有 cookie
        # 注意使用 ``httpx.post`` 而不是 ``client.post``
        post_response_with_no_persisted_cookie = httpx.post("http://localhost:8000/1", headers={"x-csrftoken": csrf})
        assert post_response_with_no_persisted_cookie.status_code == 403
        assert "CSRF token verification failed" in post_response_with_no_persisted_cookie.text

可以通过 :ref:`handler opts <handler_opts>` 将路由标记为免除此中间件提供的保护

.. code-block:: python

    @post("/post", exclude_from_csrf=True)
    def handler() -> None: ...


如果您需要一次豁免许多路由，您可能需要考虑使用
:attr:`~litestar.config.csrf.CSRFConfig.exclude` kwarg，它接受要在中间件中跳过的路径模式列表。

.. seealso::

    * `安全和不安全（HTTP 方法） <https://developer.mozilla.org/en-US/docs/Glossary/Safe/HTTP>`_
    * `HTTPX Clients <https://www.python-httpx.org/advanced/clients>`_
    * `Requests Session <https://requests.readthedocs.io/en/latest/user/advanced>`_


允许的主机
----------

另一种常见的安全机制是要求每个传入请求都有一个 ``"Host"`` 或 ``"X-Forwarded-Host"`` 标头，
然后将主机限制为特定的域集 - 即所谓的"允许的主机"。

Litestar 包含一个 :class:`~litestar.middleware.allowed_hosts.AllowedHostsMiddleware` 类，
可以通过将 :class:`~litestar.config.allowed_hosts.AllowedHostsConfig` 的实例或域列表传递给 
:class:`~litestar.app.Litestar` 来轻松启用：

.. code-block:: python

   from litestar import Litestar
   from litestar.config.allowed_hosts import AllowedHostsConfig

   app = Litestar(
       route_handlers=[...],
       allowed_hosts=AllowedHostsConfig(
           allowed_hosts=["*.example.com", "www.wikipedia.org"]
       ),
   )

.. note::

    您可以在域的开头使用通配符前缀（``*.``）来匹配子域的任何组合。因此，
    ``*.example.com`` 将匹配 ``www.example.com``，也匹配 ``x.y.z.example.com`` 等。
    您还可以简单地在受信任的主机中放入 ``*``，这意味着允许所有。这类似于关闭中间件，
    因此在这种情况下，最好一开始就不要启用它。您应该注意，通配符只能在域名的前缀中使用，
    不能在中间或末尾使用。这样做将导致引发验证异常。


压缩
----

HTML 响应可以选择性地进行压缩。Litestar 内置支持 gzip、brotli 和 zstd。
Gzip 支持通过内置的 Starlette 类提供。可以通过安装 ``brotli`` extra 添加 Brotli 支持，
通过安装 ``zstd`` extra 添加 Zstd 支持。

您可以通过将 :class:`~litestar.config.compression.CompressionConfig` 的实例传递给 
:class:`~litestar.app.Litestar` 的 ``compression_config`` 来启用任一后端。

GZIP
^^^^

您可以通过传递 ``backend`` 参数设置为 ``"gzip"`` 的 
:class:`~litestar.config.compression.CompressionConfig` 实例来启用响应的 gzip 压缩。

您可以配置以下其他 gzip 特定值：


* ``minimum_size``：启用压缩的响应大小的最小阈值。较小的响应将不会被压缩。默认为 ``500``，即半千字节。
* ``gzip_compress_level``：0-9 之间的范围，请参阅 `官方 python 文档 <https://docs.python.org/3/library/gzip.html>`_。
    默认为 ``9``，这是最大值。

.. code-block:: python

   from litestar import Litestar
   from litestar.config.compression import CompressionConfig

   app = Litestar(
       route_handlers=[...],
       compression_config=CompressionConfig(backend="gzip", gzip_compress_level=9),
   )

Brotli
^^^^^^

运行此中间件需要 `Brotli <https://pypi.org/project/Brotli>`_ 包。
它作为 litestar 的额外包提供，可以通过 ``brotli`` extra（``pip install 'litestar[brotli]'``）获得。

您可以通过传递 ``backend`` 参数设置为 ``"brotli"`` 的 
:class:`~litestar.config.compression.CompressionConfig` 实例来启用响应的 brotli 压缩。

您可以配置以下其他 brotli 特定值：


* ``minimum_size``：启用压缩的响应大小的最小阈值。较小的响应将不会被压缩。默认为 500，即半千字节
* ``brotli_quality``：范围 [0-11]，控制压缩速度与压缩密度的权衡。质量越高，压缩越慢。默认为 5
* ``brotli_mode``：压缩模式可以是 ``"generic"``（用于混合内容）、``"text"``（用于 UTF-8 格式文本输入）或
    ``"font"``（用于 WOFF 2.0）。默认为 ``"text"``
* ``brotli_lgwin``：大小的以 2 为底的对数。范围 [10-24]。默认为 22。
* ``brotli_lgblock``：最大输入块大小的以 2 为底的对数。范围 [16-24]。如果设置为 0，
    将根据质量设置该值。默认为 0
* ``brotli_gzip_fallback``：一个布尔值，指示如果不支持 brotli 是否应使用 gzip

.. code-block:: python

   from litestar import Litestar
   from litestar.config.compression import CompressionConfig

   app = Litestar(
       route_handlers=[...],
       compression_config=CompressionConfig(backend="brotli", brotli_gzip_fallback=True),
   )

Zstd
^^^^

运行此中间件需要 `Zstd <https://pypi.org/project/zstd>`_ 包。
它作为 Litestar 的额外包通过 ``zstd`` extra 提供：（``pip install 'litestar[zstd]'``）。

您可以通过传递 ``backend`` 参数设置为 ``"zstd"`` 的
:class:`~litestar.config.compression.CompressionConfig` 实例来启用响应的 zstd 压缩。

您可以配置以下其他 zstd 特定值：

* ``minimum_size``：启用压缩的响应大小的最小阈值。较小的响应将不会被压缩。默认为 500，即半千字节。
* ``zstd_level``：范围 [0-22]，控制压缩级别。较高的值会增加压缩比但速度较慢。默认为 3。
* ``zstd_gzip_fallback``：布尔值，指示如果不支持 Zstd 是否回退到 gzip。默认为 True。

.. code-block:: python

   from litestar import Litestar
   from litestar.config.compression import CompressionConfig

   app = Litestar(
       route_handlers=[...],
       compression_config=CompressionConfig(backend="zstd", zstd_gzip_fallback=True),
   )

速率限制中间件
--------------

Litestar 包含一个可选的 :class:`~litestar.middleware.rate_limit.RateLimitMiddleware`，
它遵循 `IETF RateLimit 草案规范 <https://datatracker.ietf.org/doc/draft-ietf-httpapi-ratelimit-headers/>`_。

要使用速率限制中间件，请使用 :class:`~litestar.middleware.rate_limit.RateLimitConfig`：

.. literalinclude:: /examples/middleware/rate_limit.py
    :language: python

唯一需要的配置 kwarg 是 ``rate_limit``，它需要一个包含时间单位（``"second"``、
``"minute"``、``"hour"``、``"day"``）和请求配额值（整数）的元组。


在代理后使用
^^^^^^^^^^^^

唯一标识客户端的默认模式使用客户端的地址。当应用程序在代理后运行时，
该地址将是代理的地址，而不是最终用户的"真实"地址。

虽然代理设置了特殊的标头来检索远程客户端的实际地址（``X-FORWARDED-FOR``），
但不应隐式信任它们的值，因为任何客户端都可以自由地将它们设置为他们想要的任何值。
通过欺骗这些标头，可以轻松绕过速率限制，只需为每个请求附加一个新的随机地址即可。

处理在代理后运行的应用程序的最佳方法是使用以安全方式更新客户端地址的中间件，
例如 uvicorn 的
`ProxyHeaderMiddleware <https://github.com/encode/uvicorn/blob/master/uvicorn/middleware/proxy_headers.py>`_
或 hypercon 的 `ProxyFixMiddleware <https://hypercorn.readthedocs.io/en/latest/how_to_guides/proxy_fix.html>`_。


日志记录中间件
--------------

Litestar 附带了一个强大的日志记录中间件，允许在构建 Litestar 的 
:ref:`日志记录配置 <logging-usage>` 的同时记录 HTTP 请求和响应：

.. literalinclude:: /examples/middleware/logging_middleware.py
    :language: python


日志记录中间件使用在应用程序级别定义的记录器配置，允许使用任何支持的日志记录工具，
具体取决于使用的配置（有关更多详细信息，请参阅 :ref:`日志记录配置 <logging-usage>`）。

混淆日志输出
^^^^^^^^^^^^

有时某些数据，例如请求或响应标头，需要被混淆。中间件配置支持这一点：

.. code-block:: python

   from litestar.middleware.logging import LoggingMiddlewareConfig

   logging_middleware_config = LoggingMiddlewareConfig(
       request_cookies_to_obfuscate={"my-custom-session-key"},
       response_cookies_to_obfuscate={"my-custom-session-key"},
       request_headers_to_obfuscate={"my-custom-header"},
       response_headers_to_obfuscate={"my-custom-header"},
   )

中间件将默认混淆标头 ``Authorization`` 和 ``X-API-KEY``，以及 cookie ``session``。


响应体的压缩和日志记录
^^^^^^^^^^^^^^^^^^^^^^

如果已为应用程序定义了 :class:`~litestar.config.compression.CompressionConfig` 和
:class:`~litestar.middleware.logging.LoggingMiddleware`，
即使 ``"body"`` 已包含在 
:class:`~litestar.middleware.logging.LoggingMiddlewareConfig.response_log_fields` 中，
如果响应体已被压缩，也会从响应日志记录中省略。要强制记录压缩响应的正文，
除了在 ``response_log_fields`` 中包含 ``"body"`` 之外，
还要将 :attr:`~litestar.middleware.logging.LoggingMiddlewareConfig.include_compressed_body` 
设置为 ``True``。

会话中间件
----------

Litestar 包含一个 :class:`~litestar.middleware.session.base.SessionMiddleware`，
提供客户端和服务器端会话。服务器端会话由 Litestar 的 :doc:`stores </usage/stores>` 支持，
它提供以下支持：

- 内存会话
- 基于文件的会话
- 基于 Redis 的会话
- 基于 Valkey 的会话
- 基于数据库的 :ref:`advanced-alchemy:usage/frameworks/litestar:Session Middleware`

设置中间件
^^^^^^^^^^

要开始在应用程序中使用会话，您只需创建一个 
:class:`配置 <litestar.middleware.session.base.BaseBackendConfig>` 对象的实例，
并将其中间件添加到应用程序的中间件堆栈中：

.. literalinclude:: /examples/middleware/session/cookies_full_example.py
    :caption: Hello World
    :language: python


.. note::

    由于客户端和服务器端会话都依赖于 cookie（一个用于存储实际会话数据，
    另一个用于存储会话 ID），它们共享大部分 cookie 配置。
    cookie 配置的完整参考可以在 :class:`~litestar.middleware.session.base.BaseBackendConfig` 中找到。

客户端会话
^^^^^^^^^^

客户端会话通过 :class:`~litestar.middleware.session.client_side.ClientSideSessionBackend` 提供，
它提供强大的 AES-CGM 加密安全最佳实践，同时支持 cookie 拆分。

.. important::

    ``ClientSideSessionBackend`` 需要 `cryptography <https://cryptography.io/en/latest/>`_ 库，
    可以通过 ``pip install 'litestar[cryptography]'`` 作为额外包与 litestar 一起安装

.. literalinclude:: /examples/middleware/session/cookie_backend.py
    :caption: ``cookie_backend.py``
    :language: python


.. seealso::

    * :class:`~litestar.middleware.session.client_side.CookieBackendConfig`


服务器端会话
^^^^^^^^^^^^

服务器端会话在服务器上存储数据 - 顾名思义 - 而不是在客户端。
它们使用包含会话 ID 的 cookie，会话 ID 是一个随机生成的字符串，
用于标识客户端并从存储中加载适当的数据

.. literalinclude:: /examples/middleware/session/file_store.py


.. seealso::

    * :doc:`/usage/stores`
    * :class:`~litestar.middleware.session.server_side.ServerSideSessionConfig`
