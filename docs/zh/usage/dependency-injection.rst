依赖注入
====================

Litestar 具有简单但强大的依赖注入系统，允许在应用程序的所有层声明依赖：

.. code-block:: python

   from litestar import Controller, Router, Litestar, get
   from litestar.di import Provide


   async def bool_fn() -> bool: ...


   async def dict_fn() -> dict: ...


   async def list_fn() -> list: ...


   async def int_fn() -> int: ...


   class MyController(Controller):
       path = "/controller"
       # 在控制器上
       dependencies = {"controller_dependency": Provide(list_fn)}

       # 在路由处理程序上
       @get(path="/handler", dependencies={"local_dependency": Provide(int_fn)})
       def my_route_handler(
           self,
           app_dependency: bool,
           router_dependency: dict,
           controller_dependency: list,
           local_dependency: int,
       ) -> None: ...


   # 在路由器上
   my_router = Router(
       path="/router",
       dependencies={"router_dependency": Provide(dict_fn)},
       route_handlers=[MyController],
   )

   # 在应用程序上
   app = Litestar(
       route_handlers=[my_router], dependencies={"app_dependency": Provide(bool_fn)}
   )

上面的示例说明了如何在应用程序的不同层声明依赖。

.. note::

    Litestar 在运行时需要注入的类型，这可能与 linter 规则的建议使用 ``TYPE_CHECKING`` 冲突。

    .. seealso::

        :ref:`Signature namespace <signature_namespace>`

依赖可以是可调用对象 - 同步或异步函数、方法或实现 :meth:`object.__call__` 方法的类实例，或者是类。这些依次被包装在 :class:`Provide <.di.Provide>` 类的实例中。


.. include:: /admonitions/sync-to-thread-info.rst


先决条件和作用域
------------------------

依赖注入的先决条件是：


#. 依赖必须是可调用对象。
#. 依赖可以接收 kwargs 和 ``self`` 参数，但不能接收位置参数。
#. kwarg 名称和依赖键必须相同。
#. 依赖必须使用 ``Provide`` 类声明。
#. 依赖必须在处理函数的 *作用域* 内。

在这种情况下，什么是 *作用域*？依赖 **隔离** 到它们声明的上下文。因此，在上面的示例中，``local_dependency`` 只能在声明它的特定路由处理程序内访问；``controller_dependency`` 仅适用于该特定控制器上的路由处理程序；``router dependency`` 仅适用于在该特定路由器上注册的路由处理程序。只有 ``app_dependency`` 对所有路由处理程序可用。

.. _yield_dependencies:

带有 yield 的依赖（清理步骤）
--------------------------------------

除了简单的可调用对象之外，依赖还可以是（异步）生成器函数，这允许在处理函数返回后执行额外的清理步骤，例如关闭连接。

.. admonition:: 技术细节
    :class: info

    清理阶段在处理函数返回 **之后** 执行，但在响应发送 **之前**（在 HTTP 请求的情况下）


基本示例
~~~~~~~~~~~~~~~

.. literalinclude:: /examples/dependency_injection/dependency_yield_simple.py
    :caption: ``dependencies.py``
    :language: python


如果您运行代码，您会看到 ``CONNECTION`` 在处理函数返回后已被重置：

.. code-block:: python

   from litestar.testing import TestClient
   from dependencies import app, CONNECTION

   with TestClient(app=app) as client:
       print(client.get("/").json())  # {"open": True}
       print(CONNECTION)  # {"open": False}

处理异常
~~~~~~~~~~~~~~~~~~~

如果处理函数内发生异常，它将在生成器内 **引发**，在它第一次 ``yield`` 的点。这使得可以根据异常调整依赖的行为，例如在错误时回滚数据库会话，否则提交。

.. literalinclude:: /examples/dependency_injection/dependency_yield_exceptions.py
    :caption: ``dependencies.py``
    :language: python


.. code-block:: python

   from litestar.testing import TestClient
   from dependencies import STATE, app

   with TestClient(app=app) as client:
       response = client.get("/John")
       print(response.json())  # {"John": "hello"}
       print(STATE)  # {"result": "OK", "connection": "closed"}

       response = client.get("/Peter")
       print(response.status_code)  # 500
       print(STATE)  # {"result": "error", "connection": "closed"}


.. admonition:: 最佳实践
    :class: tip

    无论您是否想要处理异常，都应该始终将 ``yield`` 包装在 ``try``/``finally`` 块中，以确保即使发生异常也会运行清理代码：

    .. code-block:: python

        def generator_dependency():
            try:
                yield
            finally:
                ...  # 清理代码


.. attention::

    不要在依赖内重新引发异常。在这些依赖中捕获的异常仍将由常规机制处理，无需显式重新引发


.. important::

    在依赖的清理步骤中引发的异常将在 :exc:`ExceptionGroup` 中重新引发（对于 Python 版本 < 3.11，将使用 `exceptiongroup <https://github.com/agronholm/exceptiongroup>`_）。这发生在所有依赖都被清理后，因此在一个依赖的清理期间引发的异常不会影响其他依赖的清理。



依赖关键字参数
----------------------------

如上所述，依赖可以接收 kwargs 但不能接收 args。这样做的原因是依赖使用解析路由处理函数的相同机制进行解析，它们也可以像路由处理函数一样将数据注入其中。

实际上，您可以注入可以 :ref:`注入到路由处理程序中的相同数据 <usage/routing/handlers:"reserved" keyword arguments>`。

.. code-block:: python

   from litestar import Controller, patch
   from litestar.di import Provide
   from pydantic import BaseModel, UUID4


   class User(BaseModel):
       id: UUID4
       name: str


   async def retrieve_db_user(user_id: UUID4) -> User: ...


   class UserController(Controller):
       path = "/user"
       dependencies = {"user": Provide(retrieve_db_user)}

       @patch(path="/{user_id:uuid}")
       async def get_user(self, user: User) -> User: ...

在上面的示例中，我们有一个 ``User`` 模型，我们将其持久化到数据库中。使用辅助方法 ``retrieve_db_user`` 获取模型，该方法接收 ``user_id`` kwarg 并检索相应的 ``User`` 实例。``UserController`` 类将 ``retrieve_db_user`` 提供程序映射到其 ``dependencies`` 字典中的键 ``user``。这反过来使其作为 ``get_user`` 方法中的 kwarg 可用。




依赖覆盖
--------------------

因为依赖是使用字符串键字典在应用的每个层声明的，所以覆盖依赖非常简单：

.. code-block:: python

   from litestar import Controller, get
   from litestar.di import Provide


   def bool_fn() -> bool: ...


   def dict_fn() -> dict: ...


   class MyController(Controller):
       path = "/controller"
       # 在控制器上
       dependencies = {"some_dependency": Provide(dict_fn)}

       # 在路由处理程序上
       @get(path="/handler", dependencies={"some_dependency": Provide(bool_fn)})
       def my_route_handler(
           self,
           some_dependency: bool,
       ) -> None: ...

较低作用域的路由处理函数声明了与较高作用域控制器上声明的依赖具有相同键的依赖。因此较低作用域的依赖会覆盖较高作用域的依赖。


``Provide`` 类
----------------------

:class:`Provide <.di.Provide>` 类是用于依赖注入的包装器。要注入可调用对象，必须将其包装在 ``Provide`` 中：

.. code-block:: python

   from random import randint
   from litestar import get
   from litestar.di import Provide


   def my_dependency() -> int:
       return randint(1, 10)


   @get(
       "/some-path",
       dependencies={
           "my_dep": Provide(
               my_dependency,
           )
       },
   )
   def my_handler(my_dep: int) -> None: ...


.. attention::

    如果 :class:`Provide.use_cache <.di.Provide>` 为 ``True``，函数的返回值将在第一次调用时被记忆化，然后将被使用。没有 kwargs 的复杂比较、LRU 实现等，因此在选择使用此选项时应该小心。请注意，即使将 ``Provide.use_cache`` 设置为 ``False``，依赖在每个请求中也只会被调用一次。



依赖中的依赖
--------------------------------

您可以将依赖注入到其他依赖中 - 就像将它们注入到常规函数中一样。

.. code-block:: python

   from litestar import Litestar, get
   from litestar.di import Provide
   from random import randint


   def first_dependency() -> int:
       return randint(1, 10)


   def second_dependency(injected_integer: int) -> bool:
       return injected_integer % 2 == 0


   @get("/true-or-false")
   def true_or_false_handler(injected_bool: bool) -> str:
       return "its true!" if injected_bool else "nope, its false..."


   app = Litestar(
       route_handlers=[true_or_false_handler],
       dependencies={
           "injected_integer": Provide(first_dependency),
           "injected_bool": Provide(second_dependency),
       },
   )

.. note::

   `依赖覆盖`_ 的规则在这里也适用。


``Dependency`` 函数
----------------------------

依赖验证
~~~~~~~~~~~~~~~~~~~~~

默认情况下，注入的依赖值由 Litestar 验证，例如，此应用程序将引发内部服务器错误：

.. literalinclude:: /examples/dependency_injection/dependency_validation_error.py
    :caption: 依赖验证错误
    :language: python


可以使用 :class:`Dependency <litestar.params.Dependency>` 函数切换依赖验证。

.. literalinclude:: /examples/dependency_injection/dependency_skip_validation.py
    :caption: 依赖验证错误
    :language: python


出于效率原因，或者如果 pydantic 无法验证某个类型，这可能很有用，但请谨慎使用！

Dependency 函数作为标记
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:class:`Dependency <litestar.params.Dependency>` 函数还可以用作标记，让我们更详细地了解您的应用程序。

从 OpenAPI 文档中排除具有默认值的依赖
***********************************************************

根据您的应用程序设计，可能会在处理程序或 :class:`Provide <.di.Provide>` 函数中声明具有默认值的依赖。如果没有为路由提供依赖，则该函数应使用默认值。

.. literalinclude:: /examples/dependency_injection/dependency_with_default.py
    :caption: 具有默认值的依赖
    :language: python


这不会失败，但由于应用程序确定参数类型的方式，它被推断为查询参数。


通过将参数声明为依赖，Litestar 知道将其从文档中排除：

.. literalinclude:: /examples/dependency_injection/dependency_with_dependency_fn_and_default.py
    :caption: 具有默认值的依赖
    :language: python


如果未提供依赖则早期检测
***********************************************

同一硬币的另一面是当没有提供依赖并且没有指定默认值时。如果没有依赖标记，参数将被假定为查询参数，并且在访问时路由很可能会失败。

如果参数被标记为依赖，这允许我们提早失败：

.. literalinclude:: /examples/dependency_injection/dependency_non_optional_not_provided.py
   :caption: 未提供依赖错误
   :language: python
