响应
=========

Litestar 提供了多种指定和处理 HTTP 响应的方式,每种方式都适合不同的使用场景。不过基本模式很简单 - 只需从路由处理器函数返回一个值,让 Litestar 处理其余的事情:

.. code-block:: python

   from pydantic import BaseModel
   from litestar import get


   class Resource(BaseModel):
       id: int
       name: str


   @get("/resources")
   def retrieve_resource() -> Resource:
       return Resource(id=1, name="my resource")

在上面的示例中,路由处理器函数返回 ``Resource`` pydantic 类的一个实例。然后 Litestar 将使用此值构造 :class:`Response <litestar.response.Response>` 类的实例,使用默认值:响应状态码将设置为 ``200``,其 ``Content-Type`` 标头将设置为 ``application/json``。``Resource`` 实例将被序列化为 JSON 并设置为响应正文。



媒体类型
----------

如果响应应该是 JSON,则不必在路由处理器函数中指定 ``media_type`` 参数。但如果您希望返回 JSON 以外的响应,则应指定此值。您可以使用 :class:`MediaType <litestar.enums.MediaType>` 枚举来实现此目的:

.. code-block:: python

   from litestar import MediaType, get


   @get("/resources", media_type=MediaType.TEXT)
   def retrieve_resource() -> str:
       return "The rumbling rabbit ran around the rock"

``media_type`` 参数的值会影响响应数据的序列化和 OpenAPI 文档的生成。上面的示例将导致 Litestar 将响应序列化为简单的字节字符串,``Content-Type`` 标头值为 ``text/plain``。它还将在 OpenAPI 文档中设置相应的值。

MediaType 具有以下成员:

* MediaType.JSON: ``application/json``
* MediaType.MessagePack: ``application/x-msgpack``
* MediaType.TEXT: ``text/plain``
* MediaType.HTML: ``text/html``

您还可以将任何 `IANA 引用的 <https://www.iana.org/assignments/media-types/media-types.xhtml>`_ 媒体类型字符串设置为 ``media_type``。虽然这仍会按预期影响 OpenAPI 生成,但您可能需要使用带有序列化器的 :ref:`自定义响应 <usage/responses:Custom Responses>` 或在路由处理器函数中序列化值来处理序列化。

JSON 响应
++++++++++++++

如前所述,默认的 ``media_type`` 是 ``MediaType.JSON``,它支持以下值:

* :doc:`dataclasses <python:library/dataclasses>`
* `pydantic dataclasses <https://docs.pydantic.dev/usage/dataclasses/>`_
* `pydantic models <https://docs.pydantic.dev/usage/models/>`_
* 扩展 pydantic 模型的库中的模型
* :class:`UUIDs <uuid.UUID>`
* :doc:`datetime objects <python:library/datetime>`
* `msgspec.Struct <https://jcristharif.com/msgspec/structs.html>`_
* 包含支持类型的容器类型,如 :class:`dict` 或 :class:`list`

如果您需要返回其他值并希望扩展序列化,可以使用 :ref:`自定义响应 <usage/responses:Custom Responses>` 来实现。

您还可以将 `RFC 6839 <https://datatracker.ietf.org/doc/html/rfc6839#section-3.1>`_ 中定义的带有 ``+json`` 后缀的应用程序媒体类型字符串设置为 ``media_type``,它将被识别并序列化为 json。

例如,您可以使用 ``application/vnd.example.resource+json``,它将像 json 一样工作,但具有适当的 content-type 标头,并显示在生成的 OpenAPI 架构中。

.. literalinclude:: /examples/responses/json_suffix_responses.py
    :language: python

MessagePack 响应
+++++++++++++++++++++

除了 JSON,Litestar 还支持 `MessagePack <https://msgpack.org/>`_ 格式,它可以是 JSON 的时间和空间高效替代方案。

它支持与 JSON 序列化相同的所有类型。要发送 ``MessagePack`` 响应,只需将媒体类型指定为 ``MediaType.MESSAGEPACK``:

.. code-block:: python

   from typing import Dict
   from litestar import get, MediaType


   @get(path="/health-check", media_type=MediaType.MESSAGEPACK)
   def health_check() -> Dict[str, str]:
       return {"hello": "world"}

纯文本响应
+++++++++++++++++++

对于 ``MediaType.TEXT``,路由处理器应返回 :class:`str` 或 :class:`bytes` 值:

.. code-block:: python

   from litestar import get, MediaType


   @get(path="/health-check", media_type=MediaType.TEXT)
   def health_check() -> str:
       return "healthy"

HTML 响应
++++++++++++++

对于 ``MediaType.HTML``,路由处理器应返回包含 HTML 的 :class:`str` 或 :class:`bytes` 值:

.. code-block:: python

   from litestar import get, MediaType


   @get(path="/page", media_type=MediaType.HTML)
   def health_check() -> str:
       return """
       <html>
           <body>
               <div>
                   <span>Hello World!</span>
               </div>
           </body>
       </html>
       """

.. tip::

   对于更复杂的 HTML 响应,最好使用 :ref:`模板引擎 <usage/templating:template engines>`,并将模板本身写入单独的文件而不是字符串。


内容协商
-------------------

如果您的处理器可以返回具有不同媒体类型的数据,并且您希望使用 `内容协商 <https://developer.mozilla.org/en-US/docs/Web/HTTP/Content_negotiation>`_ 允许客户端选择要返回的类型,则可以使用 :attr:`Request.accept <litestar.connection.Request.accept>` 属性来计算最佳匹配返回媒体类型。

.. literalinclude:: /examples/responses/response_content.py
    :language: python


状态码
------------

您可以通过将相应的 kwarg 设置为所需的值来控制响应 ``status_code``:

.. code-block:: python

   from pydantic import BaseModel
   from litestar import get
   from litestar.status_codes import HTTP_202_ACCEPTED


   class Resource(BaseModel):
       id: int
       name: str


   @get("/resources", status_code=HTTP_202_ACCEPTED)
   def retrieve_resource() -> Resource:
       return Resource(id=1, name="my resource")

如果用户未设置 ``status_code``,则使用以下默认值:


* POST: 201 (Created)
* DELETE: 204 (No Content)
* GET, PATCH, PUT: 200 (Ok)

.. attention::

    对于 < 100 或 204、304 状态的状态码,不允许有响应正文。如果您指定除 ``None`` 之外的返回注解,将引发 :class:`ImproperlyConfiguredException <litestar.exceptions.ImproperlyConfiguredException>`。

.. note::

    使用具有多个 http 方法的 ``route`` 装饰器时,默认状态码为 ``200``。``delete`` 的默认值为 ``204``,因为默认情况下假定删除操作不返回数据。但这可能不是您实现中的情况 - 因此请注意根据需要进行设置。

.. tip::

   虽然您可以将整数作为 ``status_code`` 的值写入,例如 ``200``,但最佳实践是使用常量(也在测试中)。Litestar 包含易于使用的状态,从 ``litestar.status_codes`` 导出,例如 ``HTTP_200_OK`` 和 ``HTTP_201_CREATED``。另一个选择是标准库中的 :class:`http.HTTPStatus` 枚举,它还提供了额外的功能。


返回响应
-------------------

虽然默认的响应处理适合大多数用例,但在某些情况下,您需要能够直接返回响应实例。

Litestar 允许您返回任何继承自 :class:`Response <litestar.response.Response>` 类的类。因此,下面的示例将完美运行:

.. literalinclude:: /examples/responses/returning_responses.py
    :language: python


.. attention::

    对于内置的 :class:`Template <litestar.response.Template>`、:class:`File <litestar.response.File>`、:class:`Stream <litestar.response.Stream>` 和 :class:`Redirect <litestar.response.Redirect>`,您应该使用响应"响应容器",否则将无法正确生成 OpenAPI 文档。有关更多详细信息,请参阅相应的文档部分:

    - `模板响应`_
    - `文件响应`_
    - `流式响应`_
    - `重定向响应`_


注解响应
++++++++++++++++++++

如上所示,:class:`Response <litestar.response.Response>` 类接受泛型参数。这允许 Litestar 在生成 OpenAPI 文档时推断响应正文。

.. note::

    如果未提供泛型参数,因此默认为 ``Any``,则 OpenAPI 文档将不精确。因此,请确保键入此参数,即使返回空或 ``null`` 正文时,也要使用 ``None``。

返回 ASGI 应用程序
+++++++++++++++++++++++++++

Litestar 还支持直接返回 ASGI 应用程序,就像您返回响应一样。例如:

.. code-block:: python

   from litestar import get
   from litestar.types import ASGIApp, Receive, Scope, Send


   @get("/")
   def handler() -> ASGIApp:
       async def my_asgi_app(scope: Scope, receive: Receive, send: Send) -> None: ...

       return my_asgi_app

什么是 ASGI 应用程序?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

在此上下文中,ASGI 应用程序是接受三个 ASGI 参数的任何异步可调用对象(函数、类方法或简单实现特殊 :meth:`object.__call__` dunder 方法的类):``scope``、``receive`` 和 ``send``。

例如,以下所有示例都是 ASGI 应用程序:

函数 ASGI 应用程序
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from litestar.types import Receive, Scope, Send


   async def my_asgi_app_function(scope: Scope, receive: Receive, send: Send) -> None:
       # 在这里做一些事情
       ...

方法 ASGI 应用程序
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from litestar.types import Receive, Scope, Send


   class MyClass:
       async def my_asgi_app_method(
           self, scope: Scope, receive: Receive, send: Send
       ) -> None:
           # 在这里做一些事情
           ...

类 ASGI 应用程序
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from litestar.types import Receive, Scope, Send


   class ASGIApp:
       async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
           # 在这里做一些事情
           ...

从第三方库返回响应
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

因为您可以从路由处理器返回任何 ASGI 应用程序,所以您也可以使用其他库中的任何 ASGI 应用程序。例如,您可以直接从路由处理器返回 Starlette 或 FastAPI 的响应类:

.. code-block:: python

   from starlette.responses import JSONResponse

   from litestar import get
   from litestar.types import ASGIApp


   @get("/")
   def handler() -> ASGIApp:
       return JSONResponse(content={"hello": "world"})  # type: ignore

.. attention::

   Litestar 为 ASGI 参数提供了强类型。其他库通常提供不太严格的类型,这可能会导致类型检查器在 Litestar 中使用它们的 ASGI 应用程序时报错。目前,唯一的解决方案是在相关位置添加 ``# type: ignore`` 注释。尽管如此,上面的示例将完美运行。


设置响应标头
-------------------------

Litestar 允许您使用 ``response_headers`` kwarg 定义响应标头。此 kwarg 在应用程序的所有层上都可用 - 单个路由处理器、控制器、路由器和应用程序本身:

.. literalinclude:: /examples/responses/response_headers_1.py
    :language: python


在上面的示例中,从 ``my_route_handler`` 返回的响应将具有使用给定的键+值组合从应用程序的每个层设置的标头。即它将是一个等于此的字典:

.. code-block:: json

   {
     "my-local-header": "local header",
     "controller-level-header": "controller header",
     "router-level-header": "router header",
     "app-level-header": "app header"
   }

各自的描述将用于 OpenAPI 文档。


.. tip::

    :class:`ResponseHeader <litestar.datastructures.response_header.ResponseHeader>` 是一个特殊的类,允许添加 OpenAPI 属性,如 `description` 或 `documentation_only`。如果您不需要这些,您也可以选择使用映射(如字典)来定义 `response_headers`:

    .. code-block:: python

        @get(response_headers={"my-header": "header-value"})
        async def handler() -> str: ...



动态设置标头
+++++++++++++++++++++++++++

上述详细方案非常适合静态配置的标头,但您将如何处理动态设置标头? Litestar 允许您以多种方式动态设置标头,下面我们将详细介绍两种主要模式。

使用注解响应
^^^^^^^^^^^^^^^^^^^^^^^^^

我们可以直接从路由处理器返回响应实例,并根据需要手动设置标头字典,例如:

.. literalinclude:: /examples/responses/response_headers_2.py
    :language: python


在上面的示例中,我们使用 ``response_headers`` kwarg 将 ``Random-Header`` 的 ``name`` 和 ``description`` 参数传递给 OpenAPI 文档,但我们在作为 :ref:`注解响应 <usage/responses:annotating responses>` 返回的一部分中动态设置值。为此,我们没有为其设置 ``value``,并将其指定为 ``documentation_only=True``。

使用 After Request Hook
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

另一种模式是使用 :ref:`请求后处理器 <after_request>`。我们可以在应用程序的不同层上定义处理器,如相关文档中所述。我们应该注意在相应层上记录标头:

.. literalinclude:: /examples/responses/response_headers_3.py
    :language: python


在上面的示例中,我们使用路由器级别的 ``after_request_handler`` 函数设置响应标头。因为处理器函数应用于路由器,所以我们也在路由器上设置了它的文档。

我们可以使用此模式通过根据需要覆盖标头规范来更精细地调整 OpenAPI 文档。例如,假设我们有一个正在设置的路由器级别标头和一个具有相同键但值范围不同的本地标头:

.. literalinclude:: /examples/responses/response_headers_4.py
    :language: python


预定义标头
++++++++++++++++++

Litestar 对一些常用标头有专门的实现。这些标头可以使用专用的关键字参数或作为应用程序所有层(单个路由处理器、控制器、路由器和应用程序本身)上的类属性单独设置。每一层都会覆盖其上一层 - 因此,为特定路由处理器定义的标头将覆盖其路由器上定义的标头,而路由器又将覆盖应用程序级别定义的标头。

这些标头实现允许根据关联的标头规范轻松创建、序列化和解析。

缓存控制
^^^^^^^^^^^^^

:class:`CacheControlHeader <.datastructures.headers.CacheControlHeader>` 表示 `Cache-Control 标头 <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cache-Control>`_。

下面是一个简单示例,展示如何使用它:

.. literalinclude:: /examples/datastructures/headers/cache_control.py
    :caption: Cache Control 标头
    :language: python


在此示例中,我们为整个应用程序设置了 1 个月 ``max-age`` 的 ``cache-control``,为 ``MyController`` 中的所有路由设置了 1 天的 ``max-age``,为一个特定路由 ``get_server_time`` 设置了 ``no-store``。以下是从每个端点返回的缓存控制值:


* 调用 ``/population`` 时,响应将具有 ``max-age=2628288``(1 个月)的 ``cache-control``。
* 调用 ``/chance_of_rain`` 时,响应将具有 ``max-age=86400``(1 天)的 ``cache-control``。
* 调用 ``/timestamp`` 时,响应将具有 ``no-store`` 的 ``cache-control``,这意味着不要将结果存储在任何缓存中。

ETag
^^^^

:class:`ETag <.datastructures.headers.ETag>` 表示 `ETag 标头 <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/ETag>`_。

以下是一些使用示例:

.. literalinclude:: /examples/datastructures/headers/etag.py
    :caption: 返回 ETag 标头
    :language: python


.. literalinclude:: /examples/datastructures/headers/etag_parsing.py
   :caption: 解析 ETag 标头
   :language: python


设置响应 Cookie
-------------------------

Litestar 允许您使用 ``response_cookies`` kwarg 定义响应 cookie。此 kwarg 在应用程序的所有层上都可用 - 单个路由处理器、控制器、路由器和应用程序本身:

.. literalinclude:: /examples/responses/response_cookies_1.py
    :language: python


在上面的示例中,``my_route_handler`` 返回的响应将具有由应用程序的每个层设置的 cookie。Cookie 使用 `Set-Cookie 标头 <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie>`_ 设置,上述结果为:

.. code-block:: text

   Set-Cookie: local-cookie=local value; Path=/; SameSite=lax
   Set-Cookie: controller-cookie=controller value; Path=/; SameSite=lax
   Set-Cookie: router-cookie=router value; Path=/; SameSite=lax
   Set-Cookie: app-cookie=app value; Path=/; SameSite=lax

您可以通过在较低层重新声明具有相同键的 cookie 来轻松覆盖在较高层中声明的 cookie,例如:

.. literalinclude:: /examples/responses/response_cookies_2.py
    :language: python


在两个 ``my-cookie`` 声明中,只会使用路由处理器的声明,因为它是较低层:

.. code-block:: text

   Set-Cookie: my-cookie=456; Path=/; SameSite=lax



.. tip::

    如果您的 cookie 只需要键和值,则可以使用 :class:`Mapping[str, str] <typing.Mapping>` - 如 :class:`dict` - 来提供它们:

    .. code-block:: python

        @get(response_cookies={"my-cookie": "cookie-value"})
        async def handler() -> str: ...


.. seealso::

    * :class:`Cookie 参考 <.datastructures.cookie.Cookie>`



动态设置 Cookie
++++++++++++++++++++++++++++

虽然上述方案非常适合静态 cookie 值,但它不允许使用动态 cookie。因为 cookie 从根本上说是响应标头的一种类型,所以我们可以利用与设置 :ref:`设置标头 <usage/responses:setting headers dynamically>` 相同的模式。

使用注解响应
^^^^^^^^^^^^^^^^^^^^^^^^^

我们可以直接从路由处理器返回响应实例,并根据需要手动设置 cookies 列表,例如:

.. literalinclude:: /examples/responses/response_cookies_3.py
    :language: python


在上面的示例中,我们使用 ``response_cookies`` kwarg 将 ``Random-Cookie`` 的 ``key`` 和 ``description`` 参数传递给 OpenAPI 文档,但我们在作为 :ref:`注解响应 <usage/responses:annotating responses>` 返回的一部分中动态设置值。为此,我们没有为其设置 ``value``,并将其指定为 ``documentation_only=True``。

使用 After Request Hook
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

另一种模式是使用 :ref:`请求后处理器 <after_request>`。我们可以在应用程序的不同层上定义处理器,如相关文档中所述。我们应该注意在相应层上记录 cookie:

.. literalinclude:: /examples/responses/response_cookies_4.py
    :language: python


在上面的示例中,我们使用路由器级别的 ``after_request_handler`` 函数设置 cookie。因为处理器函数应用于路由器,所以我们也在路由器上设置了它的文档。

我们可以使用此模式通过根据需要覆盖 cookie 规范来更精细地调整 OpenAPI 文档。例如,假设我们有一个正在设置的路由器级别 cookie 和一个具有相同键但值范围不同的本地 cookie:

.. literalinclude:: /examples/responses/response_cookies_5.py
   :language: python


重定向响应
------------------

重定向响应是状态码在 30x 范围内的 `特殊 HTTP 响应 <https://developer.mozilla.org/en-US/docs/Web/HTTP/Redirections>`_。

在 Litestar 中,重定向响应如下所示:

.. code-block:: python

   from litestar.status_codes import HTTP_302_FOUND
   from litestar import get
   from litestar.response import Redirect


   @get(path="/some-path", status_code=HTTP_302_FOUND)
   def redirect() -> Redirect:
       # 在这里做一些事情
       # ...
       # 最后返回重定向
       return Redirect(path="/other-path")

要返回重定向响应,您应该执行以下操作:

- 可选:为路由处理器设置适当的状态码(301、302、303、307、308)。如果未设置,将使用默认值 302。
- 注解路由处理器的返回值为返回 :class:`Redirect <.response.Redirect>`
- 返回具有所需重定向路径的 :class:`Redirect <.response.Redirect>` 类的实例

文件响应
--------------

文件响应发送文件:

.. code-block:: python

   from pathlib import Path
   from litestar import get
   from litestar.response import File


   @get(path="/file-download")
   def handle_file_download() -> File:
       return File(
           path=Path(Path(__file__).resolve().parent, "report").with_suffix(".pdf"),
           filename="report.pdf",
       )

其中 ``path`` 是要发送的文件的路径,``filename`` 是在响应 `Content-Disposition <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Disposition>`_ 附件中设置的可选文件名。


媒体类型
+++++++++++

如果提供了 ``filename``,Litestar 将尝试猜测 MIME 类型,否则回退到 ``application/octet-stream``。如果无法通过文件名推断类型,您可以通过 ``media_type`` 手动设置它

例如:

.. code-block:: python

   from pathlib import Path
   from litestar import get
   from litestar.response import File


   @get(path="/file-download", media_type="application/pdf")
   def handle_file_download() -> File:
       return File(
           path=Path(Path(__file__).resolve().parent, "report").with_suffix(".pdf"),
           filename="report.pdf",
       )


流式传输
+++++++++

文件响应以流式传输或一次性发送。这取决于文件的大小和设置的 ``chunk_size``,默认为 1 MB。如果文件超过 ``chunk_size``,将以流式传输。


文件系统
++++++++++++

:class:`~litestar.response.File` 支持 Litestar 的 *文件系统协议和注册表*。如果没有明确传递文件系统,将使用注册表的默认文件系统发送文件,该文件系统本身默认为 :class:`~litestar.file_system.BaseLocalFileSystem`,从磁盘发送文件。除了 Litestar 自己的文件系统协议外,还支持所有 `fsspec <https://filesystem-spec.readthedocs.io/en/latest/>`_ 文件系统。

.. literalinclude:: /examples/responses/file_response_fs.py
    :language: python
    :caption: 从 S3 发送文件


.. literalinclude:: /examples/responses/file_response_fs_registry.py
    :language: python
    :caption: 通过使用注册表从 S3 发送文件


流式响应
-------------------

要返回流式响应,请使用 :class:`Stream <.response.Stream>` 类。该类接收一个位置参数,必须是传递流的迭代器:

.. literalinclude:: /examples/responses/streaming_responses.py
    :language: python


.. note::

    您可以为迭代器使用不同类型的值。它可以是返回同步或异步生成器的可调用对象、生成器本身、同步或异步迭代器类,或同步或异步迭代器类的实例。


服务器发送事件响应
---------------------------

要向前端发送 `服务器发送事件` 或 SSE,请使用 :class:`ServerSentEvent <.response.ServerSentEvent>` 类。该类接收一个 content 参数。您还可以指定 ``event_type``,这是在浏览器中声明的事件名称;``event_id``,设置事件源属性;``comment_message``,用于发送 ping;以及 ``retry_duration``,指示重试持续时间。

.. literalinclude:: /examples/responses/sse_responses.py
    :language: python


.. note::

    您可以为迭代器使用不同类型的值。它可以是返回同步或异步生成器的可调用对象、生成器本身、同步或异步迭代器类,或同步或异步迭代器类的实例。

在迭代器函数中,您可以 yield 整数、字符串或字节,在这种情况下发送的消息如果 ServerSentEvent 没有设置 ``event_type``,将具有 ``message`` 作为 ``event_type``,否则将使用指定的 ``event_type``,数据将是 yielded 值。

如果要发送不同的事件类型,可以使用带有键 ``event_type`` 和 ``data`` 的字典或 :class:`ServerSentEventMessage <.response.ServerSentEventMessage>` 类。

.. note::

    您可以通过直接使用 :class:`ServerSentEvent <.response.ServerSentEvent>` 类或使用 :class:`ServerSentEventMessage <.response.ServerSentEventMessage>` 或具有适当键的字典来进一步自定义所有 sse 参数、添加注释并设置重试持续时间。


模板响应
------------------

模板响应用于将模板渲染为 HTML。要使用模板响应,您必须首先在应用程序级别 :ref:`注册模板引擎 <usage/templating:registering a template engine>`。一旦引擎就位,您就可以像这样使用模板响应:

.. code-block:: python

   from litestar import Request, get
   from litestar.response import Template


   @get(path="/info")
   def info(request: Request) -> Template:
       return Template(template_name="info.html", context={"user": request.user})

在上面的示例中,:class:`Template <.response.Template>` 传递了模板名称(这是一个类似路径的值)和一个上下文字典,该字典将字符串键映射到将在模板中渲染的值。

自定义响应
----------------

虽然 Litestar 默认支持许多类型的序列化,但有时您想返回不支持的内容。在这些情况下,使用自定义响应类很方便。

下面的示例说明了如何处理 :class:`MultiDict <.datastructures.MultiDict>` 实例。

.. literalinclude:: /examples/responses/custom_responses.py
    :language: python

.. admonition:: 分层架构
    :class: seealso

    响应类是 Litestar 分层架构的一部分,这意味着您可以在应用程序的每一层上设置响应类。如果您在多个层上设置了响应类,则最接近路由处理器的层将优先。

    您可以在此处阅读更多信息::ref:`usage/applications:layered architecture`

后台任务
----------------

所有 Litestar 响应都允许传入 ``background`` kwarg。此 kwarg 接受 :class:`BackgroundTask <.background_tasks.BackgroundTask>` 的实例或 :class:`BackgroundTasks <.background_tasks.BackgroundTasks>` 的实例,后者包装 :class:`BackgroundTask <.background_tasks.BackgroundTask>` 实例的可迭代对象。

后台任务是同步或异步可调用对象(函数、方法或实现 :meth:`object.__call__` dunder 方法的类),将在响应完成发送数据后调用。

因此,在以下示例中,传入的后台任务将在响应发送后执行:

.. literalinclude:: /examples/responses/background_tasks_1.py
    :caption: 后台任务传入响应
    :language: python

当调用 ``greeter`` 处理器时,将使用传入 :class:`BackgroundTask <.background_tasks.BackgroundTask>` 的任何 ``*args`` 和 ``**kwargs`` 调用日志记录任务。

.. note::

    在上面的示例中,``"greeter"`` 是一个 arg,``message=f"was called with name {name}"`` 是一个 kwarg。``logging_task`` 的函数签名允许这样做,因此这应该不会造成问题。:class:`BackgroundTask <.background_tasks.BackgroundTask>` 使用 :class:`ParamSpec <typing.ParamSpec>` 进行类型化,从而对传递给它的参数和关键字参数进行正确的类型检查。

路由装饰器(例如 ``@get``、``@post`` 等)也允许使用 ``background`` kwarg 传入后台任务:

.. literalinclude:: /examples/responses/background_tasks_2.py
    :caption: 后台任务传入装饰器
    :language: python


.. note::

    将后台任务传入装饰器时,无法将路由处理器参数传递给后台任务。

执行多个后台任务
+++++++++++++++++++++++++++++++++++

您还可以使用 :class:`BackgroundTasks <.background_tasks.BackgroundTasks>` 类并向其传递 :class:`BackgroundTask <.background_tasks.BackgroundTask>` 实例的可迭代对象(:class:`list`、:class:`tuple` 等):

.. literalinclude:: /examples/responses/background_tasks_3.py
    :caption: 多个后台任务
    :language: python


:class:`BackgroundTasks <.background_tasks.BackgroundTasks>` 类接受可选的关键字参数 ``run_in_task_group``,默认值为 ``False``。将其设置为 ``True`` 允许后台任务并发运行,使用 `anyio.task_group <https://anyio.readthedocs.io/en/stable/tasks.html>`_。

.. note::

   将 ``run_in_task_group`` 设置为 ``True`` 不会保留执行顺序。

分页
-----------

当您需要从端点返回大量项时,通常的做法是使用分页以确保客户端可以请求总数据集中的特定子集或"页面"。Litestar 开箱即用地支持三种类型的分页:

* 经典分页
* 限制/偏移分页
* 游标分页

经典分页
++++++++++++++++++

在经典分页中,数据集被划分为特定大小的页面,然后使用者请求特定页面。

.. literalinclude:: /examples/pagination/using_classic_pagination.py
    :caption: 经典分页
    :language: python

此分页的数据容器称为 :class:`ClassicPagination <.pagination.ClassicPagination>`,这是上面示例中分页器将返回的内容。这还将生成相应的 OpenAPI 文档。

如果您需要异步逻辑,可以实现 :class:`AbstractAsyncClassicPaginator <.pagination.AbstractAsyncClassicPaginator>` 而不是 :class:`AbstractSyncClassicPaginator <.pagination.AbstractSyncClassicPaginator>`。

偏移分页
+++++++++++++++++

在偏移分页中,使用者请求由 ``limit`` 指定的项数和从数据集开头的 ``offset``。例如,给定 50 个项的列表,您可以请求 ``limit=10``、``offset=39`` 以请求第 40-50 项。

.. literalinclude:: /examples/pagination/using_offset_pagination.py
    :caption: 偏移分页
    :language: python

此分页的数据容器称为 :class:`OffsetPagination <.pagination.OffsetPagination>`,这是上面示例中分页器将返回的内容。这还将生成相应的 OpenAPI 文档。

如果您需要异步逻辑,可以实现 :class:`AbstractAsyncOffsetPaginator <.pagination.AbstractAsyncOffsetPaginator>` 而不是 :class:`AbstractSyncOffsetPaginator <.pagination.AbstractSyncOffsetPaginator>`。

使用 SQLAlchemy 的偏移分页
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

使用 SQLAlchemy 从数据库检索分页数据时,Paginator 实例需要一个 SQLAlchemy 会话实例来进行查询。这可以通过 :doc:`/usage/dependency-injection` 实现


游标分页
+++++++++++++++++

在游标分页中,使用者请求由 ``results_per_page`` 指定的项数和一个 ``cursor``,在该游标之后给出结果。游标是数据集中的唯一标识符,用作指向起始位置的方式。

.. literalinclude:: /examples/pagination/using_cursor_pagination.py
    :caption: 游标分页
    :language: python

此分页的数据容器称为 :class:`CursorPagination <.pagination.CursorPagination>`,这是上面示例中分页器将返回的内容。这还将生成相应的 OpenAPI 文档。

如果您需要异步逻辑,可以实现 :class:`AbstractAsyncCursorPaginator <.pagination.AbstractAsyncCursorPaginator>` 而不是 :class:`AbstractSyncCursorPaginator <.pagination.AbstractSyncCursorPaginator>`。
