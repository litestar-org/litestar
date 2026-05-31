测试
=======

Litestar 应用程序的测试通过开箱即用的测试工具变得简单。
基于 `httpx <https://www.python-httpx.org/>`_，它们具有熟悉的接口，并无缝集成到同步或异步测试中。


测试客户端
------------

Litestar 提供 2 个测试客户端：

- :class:`~litestar.testing.AsyncTestClient`：在异步环境中使用的异步测试客户端。它在外部管理的事件循环上运行应用程序和客户端。非常适合测试异步行为，或处理异步资源时
- :class:`~litestar.testing.TestClient`：同步测试客户端。它在单独线程中新创建的事件循环中运行应用程序。非常适合不需要测试异步行为且测试库不提供外部事件循环的情况


假设我们有一个非常简单的带有健康检查端点的应用：

.. code-block:: python
    :caption: ``my_app/main.py``

    from litestar import Litestar, MediaType, get


    @get(path="/health-check", media_type=MediaType.TEXT)
    def health_check() -> str:
        return "healthy"


    app = Litestar(route_handlers=[health_check])


然后我们会像这样使用测试客户端进行测试：

.. tab-set::

    .. tab-item:: 同步
        :sync: sync

        .. code-block:: python
            :caption: ``tests/test_health_check.py``

            from litestar.status_codes import HTTP_200_OK
            from litestar.testing import TestClient

            from my_app.main import app

            app.debug = True


            def test_health_check():
                with TestClient(app=app) as client:
                    response = client.get("/health-check")
                    assert response.status_code == HTTP_200_OK
                    assert response.text == "healthy"

    .. tab-item:: 异步
        :sync: async

        .. code-block:: python
            :caption: ``tests/test_health_check.py``

            from litestar.status_codes import HTTP_200_OK
            from litestar.testing import AsyncTestClient

            from my_app.main import app

            app.debug = True


            async def test_health_check():
                async with AsyncTestClient(app=app) as client:
                    response = await client.get("/health-check")
                    assert response.status_code == HTTP_200_OK
                    assert response.text == "healthy"


由于我们可能需要在多个地方使用客户端，最好将其制作成 pytest fixture：


.. tab-set::

    .. tab-item:: 同步
        :sync: sync

        .. code-block:: python
            :caption: ``tests/conftest.py``

            from typing import TYPE_CHECKING, Iterator

            import pytest

            from litestar.testing import TestClient

            from my_app.main import app

            if TYPE_CHECKING:
                from litestar import Litestar

            app.debug = True


            @pytest.fixture(scope="function")
            def test_client() -> Iterator[TestClient[Litestar]]:
                with TestClient(app=app) as client:
                    yield client


    .. tab-item:: 异步
        :sync: async

        .. code-block:: python
            :caption: ``tests/conftest.py``

            from typing import TYPE_CHECKING, AsyncIterator

            import pytest

            from litestar.testing import AsyncTestClient

            from my_app.main import app

            if TYPE_CHECKING:
                from litestar import Litestar

            app.debug = True


            @pytest.fixture(scope="function")
            async def test_client() -> AsyncIterator[AsyncTestClient[Litestar]]:
                async with AsyncTestClient(app=app) as client:
                    yield client


然后我们就可以像这样重写我们的测试：

.. tab-set::

    .. tab-item:: 同步
        :sync: sync

        .. literalinclude:: /examples/testing/test_health_check_sync.py
            :caption: ``tests/test_health_check.py``
            :language: python


    .. tab-item:: 异步
        :sync: async

        .. literalinclude:: /examples/testing/test_health_check_async.py
            :caption: ``tests/test_health_check.py``
            :language: python


决定使用哪个测试客户端
+++++++++++++++++++++++++++++++++

在大多数情况下，它不会产生功能上的差异，只是归结为偏好，因为两个客户端都提供相同的 API 和功能。但是，在某些情况下，客户端运行和与应用程序交互的方式很重要，特别是在异步上下文中进行测试时。

使用 `anyio 的 pytest 插件 <https://anyio.readthedocs.io/en/stable/testing.html>`_ 或 `pytest-asyncio <https://github.com/pytest-dev/pytest-asyncio>`_ 运行异步测试或 fixtures 时，一个常见的问题是使用同步 :class:`~litestar.testing.TestClient` 意味着应用程序将在与测试或 fixture *不同的事件循环* 中运行。在实践中，这可能会导致一些难以调试和解决的情况，特别是在应用程序外部设置异步资源时，例如使用工厂模式时。

以下示例使用 ``httpx.AsyncClient`` 的共享实例。它使用常见的工厂函数，允许为测试自定义客户端，例如添加身份验证标头。

.. literalinclude:: /examples/testing/async_resource_test_issue.py
    :language: python

运行此测试将失败，并在尝试关闭 ``AsyncClient`` 实例时出现 ``RuntimeError: Event loop is closed``。这是因为：

- ``http_test_client`` fixture 在 *事件循环 A* 中设置客户端
- 在 ``test_handler`` 测试中创建的 ``TestClient`` 实例设置 *事件循环 B* 并在其中运行应用程序
- 调用 ``http_client.get`` 时，``httpx.AsyncClient`` 实例在 *循环 B* 中创建一个新连接并将其附加到客户端实例
- ``TestClient`` 实例关闭 *事件循环 B*
- ``http_test_client`` fixture 的清理步骤在 *循环 A* 中调用 ``httpx.AsyncClient.aclose()`` 实例，内部尝试关闭上一步中建立的连接。然而，该连接仍然附加到由 ``TestClient`` 实例拥有的 *循环 B*，现在已关闭


这可以通过将测试从 :class:`~litestar.testing.TestClient` 切换到 :class:`~litestar.testing.AsyncTestClient` 来轻松修复：

.. literalinclude:: /examples/testing/async_resource_test_issue_fix.py
    :language: python

现在 fixture、测试和应用程序代码都在同一事件循环中运行，确保所有资源都可以正确清理而不会出现问题。

.. literalinclude:: /examples/testing/event_loop_demonstration.py
    :language: python
    :caption: 展示使用 ``TestClient`` 时的不同运行事件循环


测试 websockets
++++++++++++++++++

Litestar 的测试客户端增强了 httpx 客户端以支持 websockets。要测试 websocket 端点，可以使用测试客户端上的 :meth:`websocket_connect <litestar.testing.TestClient.websocket_connect>` 方法。该方法返回一个 websocket 连接对象，可以使用它发送和接收消息，请参见以下 json 示例：

有关更多信息，另请参阅 API 文档中的 :class:`WebSocket <litestar.connection.WebSocket>` 类和 :ref:`websocket <usage/websockets:websockets>` 文档。


.. tab-set::

    .. tab-item:: 同步
        :sync: sync

        .. literalinclude:: /examples/testing/test_websocket_sync.py
            :language: python

    .. tab-item:: 异步
        :sync: async

        .. literalinclude:: /examples/testing/test_websocket_async.py
            :language: python


使用会话
++++++++++++++

如果您使用 :ref:`会话中间件 <usage/middleware/builtin-middleware:session middleware>` 在请求之间持久化会话，那么您可能希望在请求之外注入或检查会话数据。为此，:class:`TestClient <.testing.TestClient>` 提供了两个方法：

* :meth:`set_session_data <litestar.testing.TestClient.set_session_data>`
* :meth:`get_session_data <litestar.testing.TestClient.get_session_data>`


.. tab-set::

    .. tab-item:: 同步
        :sync: sync

        .. literalinclude:: /examples/testing/test_set_session_data.py
            :caption: 设置会话数据
            :language: python


        .. literalinclude:: /examples/testing/test_get_session_data.py
            :caption: 获取会话数据
            :language: python

    .. tab-item:: 异步
        :sync: async

        .. literalinclude:: /examples/testing/test_set_session_data_async.py
            :caption: 设置会话数据
            :language: python


        .. literalinclude:: /examples/testing/test_get_session_data_async.py
            :caption: 获取会话数据
            :language: python


在 TestClient 上运行异步函数
+++++++++++++++++++++++++++++++++++++

使用同步 :class:`TestClient <.testing.TestClient>` 时，它在单独的线程中运行应用程序，该线程提供事件循环。为此，它使用 :class:`anyio.BlockingPortal <anyio.abc.BlockingPortal>`。

``TestClient`` 使此 portal 公开，因此可以用于在与应用程序相同的事件循环中运行任意异步代码：

.. literalinclude:: /examples/testing/test_with_portal.py
   :caption: 使用阻塞 portal
   :language: python


创建测试应用
-------------------

Litestar 还提供了一个名为 :func:`create_test_client <litestar.testing.create_test_client>` 的辅助函数，它首先创建一个 Litestar 实例，然后使用它创建一个测试客户端。此辅助函数有多种用例 - 当您需要检查与特定 Litestar 应用程序解耦的通用逻辑时，或者当您想要单独测试端点时。

.. code-block:: python
    :caption: ``my_app/tests/test_health_check.py``

    from litestar.status_codes import HTTP_200_OK
    from litestar.testing import create_test_client

    from my_app.main import health_check

    def test_health_check():
        with create_test_client([health_check]) as client:
            response = client.get("/health-check")
            assert response.status_code == HTTP_200_OK
            assert response.text == "healthy"


运行实时服务器
---------------------

测试客户端利用 HTTPX 直接调用 ASGI 应用的能力，而无需运行实际的服务器。在大多数情况下这已经足够，但在某些情况下这不起作用，因为模拟的客户端-服务器通信的局限性。

例如，当使用带有无限生成器的服务器发送事件时，它会锁定测试客户端，因为 HTTPX 在返回请求之前尝试消耗完整的响应。

Litestar 提供了两个辅助函数，:func:`litestar.testing.subprocess_sync_client` 和 :func:`litestar.testing.subprocess_async_client`，它们将在子进程中启动 Litestar 实例并设置 httpx 客户端来运行测试。您可以加载实际的应用文件，也可以像使用常规测试客户端设置一样从中创建子集：

.. literalinclude:: /examples/testing/subprocess_sse_app.py
    :language: python

.. literalinclude:: /examples/testing/test_subprocess_sse.py
    :language: python

RequestFactory
--------------

另一个辅助工具是 :class:`RequestFactory <litestar.testing.RequestFactory>` 类，它创建 :class:`litestar.connection.request.Request <litestar.connection.request.Request>` 的实例。此辅助工具的用例是当您需要测试期望接收请求对象的逻辑时。

例如，假设我们想要单独对 *guard* 函数进行单元测试，为此我们将重用 :doc:`路由守卫 </usage/security/guards>` 文档中的示例：


.. code-block:: python
    :caption: ``my_app/guards.py``

    from litestar import Request
    from litestar.exceptions import NotAuthorizedException
    from litestar.handlers.base import BaseRouteHandler


    def secret_token_guard(request: Request, route_handler: BaseRouteHandler) -> None:
        if (
            route_handler.opt.get("secret")
            and not request.headers.get("Secret-Header", "") == route_handler.opt["secret"]
        ):
            raise NotAuthorizedException()

我们的路由处理程序已经就位：

.. code-block:: python
    :caption: ``my_app/secret.py``

    from os import environ

    from litestar import get

    from my_app.guards import secret_token_guard


    @get(path="/secret", guards=[secret_token_guard], opt={"secret": environ.get("SECRET")})
    def secret_endpoint() -> None: ...

因此，我们可以像这样测试守卫函数：

.. code-block:: python
    :caption: ``tests/guards/test_secret_token_guard.py``

    import pytest

    from litestar.exceptions import NotAuthorizedException
    from litestar.testing import RequestFactory

    from my_app.guards import secret_token_guard
    from my_app.secret import secret_endpoint

    request = RequestFactory().get("/")


    def test_secret_token_guard_failure_scenario():
        copied_endpoint_handler = secret_endpoint.copy()
        copied_endpoint_handler.opt["secret"] = None
        with pytest.raises(NotAuthorizedException):
            secret_token_guard(request=request, route_handler=copied_endpoint_handler)


    def test_secret_token_guard_success_scenario():
        copied_endpoint_handler = secret_endpoint.copy()
        copied_endpoint_handler.opt["secret"] = "super-secret"
        secret_token_guard(request=request, route_handler=copied_endpoint_handler)
