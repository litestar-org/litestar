从 Starlette / FastAPI 迁移
==============================

路由装饰器
~~~~~~~~~~~~~~~~~~

Litestar 不在 ``Router`` 或 ``Litestar`` 实例中包含任何装饰器。
相反，所有路由都使用 :doc:`路由处理器 </usage/routing/handlers>` 声明，可以是独立函数或
控制器方法。然后可以在应用程序或路由器实例上注册处理器。

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            from fastapi import FastAPI


            app = FastAPI()


            @app.get("/")
            async def index() -> dict[str, str]: ...

    .. tab-item:: Starlette
        :sync: starlette


        .. code-block:: python

            from starlette.applications import Starlette
            from starlette.routing import Route


            async def index(request): ...


            routes = [Route("/", endpoint=index)]

            app = Starlette(routes=routes)

    .. tab-item:: Litestar
        :sync: litestar

        .. code-block:: python

           from litestar import Litestar, get


           @get("/")
           async def index() -> dict[str, str]: ...


           app = Litestar([index])


..  seealso::

    要了解有关注册路由的更多信息，请查看文档中的本章：

    * :ref:`路由 - 注册路由 <usage/routing/overview:registering routes>`

路由器和路由
~~~~~~~~~~~~~~~~~~

Litestar 和 Starlette 的 ``Router`` 类之间有几个关键区别：

1. Litestar 版本不是 ASGI 应用程序
2. Litestar 版本不包含装饰器：使用 :doc:`路由处理器 </usage/routing/handlers>`。
3. Litestar 版本不支持生命周期挂钩：这些必须在应用程序层处理。请参阅 :doc:`生命周期挂钩 </usage/lifecycle-hooks>`

如果您正在使用 Starlette 的 ``Route``，则需要将它们替换为 :doc:`路由处理器 </usage/routing/handlers>`。

基于主机的路由
~~~~~~~~~~~~~~~~~~

有意不支持基于主机的路由类。如果您的应用程序依赖于 ``Host``，您将必须将逻辑分离到不同的服务中，并使用像 `nginx <https://www.nginx.com/>`_ 或 `traefik <https://traefik.io/>`_ 这样的代理服务器来处理这部分请求分派。

依赖注入
~~~~~~~~~~~~~~~~~~~~

Litestar 依赖注入系统与 FastAPI 使用的系统不同。您可以在文档的 :doc:`依赖注入 </usage/dependency-injection>` 部分阅读相关内容。

在 FastAPI 中，您将依赖项声明为传递给 ``Router`` 或 ``FastAPI`` 实例的函数列表，或作为包装在 ``Depends`` 类实例中的默认函数参数值。

在 Litestar 中，**依赖项始终使用字典声明**，其中键是字符串，值包装在 ``Provide`` 类的实例中。这也允许在应用程序的每个级别透明地覆盖依赖项，并轻松访问更高级别的依赖项。

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

           from fastapi import FastAPI, Depends, APIRouter


           async def route_dependency() -> bool: ...


           async def nested_dependency() -> str: ...


           async def router_dependency() -> int: ...


           async def app_dependency(data: str = Depends(nested_dependency)) -> int: ...


           router = APIRouter(dependencies=[Depends(router_dependency)])
           app = FastAPI(dependencies=[Depends(nested_dependency)])
           app.include_router(router)


           @app.get("/")
           async def handler(
               val_route: bool = Depends(route_dependency),
               val_router: int = Depends(router_dependency),
               val_nested: str = Depends(nested_dependency),
               val_app: int = Depends(app_dependency),
           ) -> None: ...



    .. tab-item:: Litestar
        :sync: litestar

        .. code-block:: python

           from litestar import Litestar, get, Router
           from litestar.di import Provide


           async def route_dependency() -> bool: ...


           async def nested_dependency() -> str: ...


           async def router_dependency() -> int: ...


           async def app_dependency(nested: str) -> int: ...


           @get("/", dependencies={"val_route": Provide(route_dependency)})
           async def handler(
               val_route: bool, val_router: int, val_nested: str, val_app: int
           ) -> None: ...


           router = Router(dependencies={"val_router": Provide(router_dependency)})
           app = Litestar(
               route_handlers=[handler],
               dependencies={
                   "val_app": Provide(app_dependency),
                   "val_nested": Provide(nested_dependency),
               },
           )


..  seealso::

    要了解有关依赖注入的更多信息，请查看文档中的本章：

    * :doc:`/usage/dependency-injection`

生命周期
~~~~~~~~

Litestar 使用与 FastAPI 相同的异步上下文管理器风格，因此代码不需要更改：

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            @asynccontextmanager
            async def lifespan(
                app: FastAPI
            ):
                # 设置代码在这里
                yield
                # 清理代码在这里

    .. tab-item:: Litestar
        :sync: litestar

        .. code-block:: python

            @asynccontextmanager
            async def lifespan(
                app: Litestar
            ):
                # 设置代码在这里
                yield
                # 清理代码在这里


Cookies
~~~~~~~

在 FastAPI 中，您通常在 ``Response`` 对象上设置 cookie，而在 Litestar 中有两个选项：在装饰器级别使用 ``response_cookies`` 关键字参数，或在响应级别动态设置（请参阅：:ref:`动态设置 Cookies <usage/responses:setting cookies dynamically>`）

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            @app.get("/")
            async def index(response: Response) -> dict[str, str]:
                response.set_cookie(key="my_cookie", value="cookie_value")
                ...

    .. tab-item:: Litestar
        :sync: litestar

        .. code-block:: python

            @get(response_cookies={"my-cookie": "cookie-value"})
            async def handler() -> str:
                ...


依赖项参数
~~~~~~~~~~~~~~~~~~~~~~~
FastAPI 和 Litestar 之间传递依赖项参数的方式不同，请注意 Litestar 示例中的 ``state: State`` 参数。
您可以通过处理器中的 state 关键字参数或 ``request.state``（它们指向同一个对象，一个从应用程序状态继承的请求本地状态）获取状态，或者通过 `request.app.state` 获取应用程序的状态。

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            from fastapi import Request

            async def get_arqredis(request: Request) -> ArqRedis:
                return request.state.arqredis

    .. tab-item:: Litestar
        :sync: litestar

        .. code-block:: python

            from litestar import State

            async def get_arqredis(state: State) -> ArqRedis:
                return state.arqredis

Post json
~~~~~~~~~

在 FastAPI 中，您直接将 JSON 对象作为参数传递给端点，然后由 Pydantic 进行验证。在 Litestar 中，您使用 `data` 关键字参数。数据将由相关的建模库解析和验证。

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python


            class ObjectType(BaseModel):
                name: str

            @app.post("/items/")
            async def create_item(object_name: ObjectType) -> dict[str, str]:
                return {"name": object_name.name}

    .. tab-item:: Litestar
        :sync: litestar

        .. code-block:: python

            from litestar import Litestar, post
            from pydantic import BaseModel

            class ObjectType(BaseModel):
                name: str

            @post("/items/")
            async def create_item(data: ObjectType) -> dict[str, str]:
                return {"name": data.name}


默认状态码
~~~~~~~~~~~~~~~~~~~~

Post 在 FastAPI 中默认为 200，在 Litestar 中默认为 201。

模板
~~~~~~~~~

在 FastAPI 中，您使用 `TemplateResponse` 来渲染模板。在 Litestar 中，您使用 `Template` 类。
此外，FastAPI 允许您传递字典，而在 Litestar 中您需要显式传递 context 关键字参数。

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            @app.get("/uploads")
            async def get_uploads(request: Request):
                return templates.TemplateResponse(
                    "uploads.html", {"request": request, "debug": app.state.debug}
                )

    .. tab-item:: Litestar
        :sync: litestar

        .. code-block:: python

            @get("/uploads")
            async def get_uploads(app_settings) -> Template:
                return Template(
                    name="uploads.html", context={"debug": app_settings.debug}
                )

默认处理器名称
~~~~~~~~~~~~~~~~~~~~~~~

在 FastAPI 中，处理器名称默认为函数的本地名称。在 Litestar 中，您需要在路由装饰器中显式声明 `name` 参数。这在使用例如 `url_for` 时很重要。

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            @app.get("/blabla")
            async def blabla() -> str:
                return "Blabla"
        .. code-block:: html

            <a href="{{ url_for('blabla') }}">Blabla</a>

    .. tab-item:: Litestar
        :sync: litestar

        .. code-block:: python

            @get(path="/blabla", name="blabla")
            async def blabla() -> str:
                return "Blabla"

        .. code-block:: html

            <a href="{{ url_for('blabla') }}">Blabla</a>

上传
~~~~~~~

在 FastAPI 中，您使用 `File` 类来处理文件上传。在 Litestar 中，您使用 `data` 关键字参数与 `Body` 并将 `media_type` 指定为 `RequestEncodingType.MULTI_PART`。
虽然这更冗长，但它也更明确，更清楚地传达了意图。

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            @app.post("/upload/")
            async def upload_file(files: list[UploadFile] = File(...)) -> dict[str, str]:
                return {"file_names": [file.filename for file in files]}

    .. tab-item:: Litestar
        :sync: litestar

        .. code-block:: python

            @post("/upload/")
            async def upload_file(data: Annotated[list[UploadFile], Body(media_type=RequestEncodingType.MULTI_PART)]) -> dict[str, str]:
                return {"file_names": [file.filename for file in data]}

            app = Litestar([upload_file])


异常签名
~~~~~~~~~~~~~~~~~~~~

在 FastAPI 中，状态码和异常详细信息可以作为位置参数传递给 `HTTPException`，而在 Litestar 中它们使用关键字参数设置，例如 `status_code`。Litestar 中 `HTTPException` 的位置参数将添加到异常详细信息中。
如果迁移时只是更改 HTTPException 导入，这将导致错误。

.. tab-set::

    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            from fastapi import FastAPI, HTTPException

            app = FastAPI()

            @app.get("/")
            async def index() -> None:
                response_fields = {"array": "value"}
                raise HTTPException(
                    400, detail=f"can't get that field: {response_fields.get('array')}"
                )

    .. tab-item:: Litestar
        :sync: litestar

        .. code-block:: python

            from litestar import Litestar, get
            from litestar.exceptions import HTTPException

            @get("/")
            async def index() -> None:
                response_fields = {"array": "value"}
                raise HTTPException(
                    status_code=400, detail=f"can't get that field: {response_fields.get('array')}"
                )

            app = Litestar([index])


认证
~~~~~~~~~~~~~~

FastAPI 推广使用依赖注入模式进行身份验证。您可以在 Litestar 中做同样的事情，但首选的处理方式是扩展 :doc:`/usage/security/abstract-authentication-middleware`。

.. tab-set::
    .. tab-item:: FastAPI
        :sync: fastapi

        .. code-block:: python

            from fastapi import FastAPI, Depends, Request


            async def authenticate(request: Request) -> None: ...


            app = FastAPI()


            @app.get("/", dependencies=[Depends(authenticate)])
            async def index() -> dict[str, str]: ...


    .. tab-item:: Litestar
        :sync: litestar

        .. code-block:: python

            from litestar import Litestar, get, ASGIConnection, BaseRouteHandler


            async def authenticate(
                connection: ASGIConnection, route_handler: BaseRouteHandler
            ) -> None: ...


            @get("/", guards=[authenticate])
            async def index() -> dict[str, str]: ...


..  seealso::

    要了解有关安全性和身份验证的更多信息，请查看文档中的本章：

    * :doc:`/usage/security/index`

依赖项覆盖
~~~~~~~~~~~~~~~~~~~~

虽然 FastAPI 包含在现有应用程序对象上覆盖依赖项的机制，
但 Litestar 推广针对此问题的架构解决方案。因此，在 Litestar 中覆盖依赖项仅在定义时严格支持，即当您定义处理器、控制器、路由器和应用程序时。依赖项覆盖在根本上与模拟是相同的想法，应该以同样的谨慎态度对待，并谨慎使用，而不是作为默认方式。

要达到相同的效果，有三种通用方法：

1. 在设计应用程序时考虑不同的环境。例如，这可能意味着根据环境连接到不同的数据库，而环境反过来通过环境变量设置。这在大多数情况下是足够的，围绕这一原则设计应用程序是一种良好的通用实践，因为它促进了可配置性和集成测试能力
2. 隔离单元测试的测试并使用 ``create_test_client``
3. 如果上述方法都不起作用，则采用模拟

中间件
~~~~~~~~~~

纯 ASGI 中间件完全兼容，可以与任何 ASGI 框架一起使用。使用 FastAPI/Starlette 特定中间件功能的中间件，例如 Starlette 的 `BaseHTTPMiddleware <https://www.starlette.io/middleware/#basehttpmiddleware>`_ 不兼容，但可以通过 :doc:`创建中间件 </usage/middleware/creating-middleware>` 轻松替换。
