-----------------------------
配置 Schema 生成
-----------------------------

OpenAPI schema 生成默认启用。要配置它，您可以使用 ``openapi_config`` kwarg 
将 :class:`OpenAPIConfig <.openapi.OpenAPIConfig>` 的实例传递给 :class:`Litestar <litestar.app.Litestar>` 类：

.. code-block:: python

   from litestar import Litestar
   from litestar.openapi import OpenAPIConfig

   app = Litestar(
       route_handlers=[...], openapi_config=OpenAPIConfig(title="My API", version="1.0.0")
   )



禁用 Schema 生成
++++++++++++++++

如果您希望禁用 schema 生成并且不在 API 中包含 schema 端点，只需将 ``None`` 作为 ``openapi_config`` 的值传递：

.. code-block:: python

   from litestar import Litestar

   app = Litestar(route_handlers=[...], openapi_config=None)



在路由处理器上配置 Schema 生成
---------------------------------

默认情况下，为所有路由处理器生成 `operation <https://spec.openapis.org/oas/latest.html#operation-object>`_ schema。
您可以通过设置 ``include_in_schema=False`` 从 schema 中省略路由处理器：

.. code-block:: python

   from litestar import get


   @get(path="/some-path", include_in_schema=False)
   def my_route_handler() -> None: ...

您还可以使用以下 kwargs 修改路由处理器生成的 schema：

``tags``
    与 `tag 规范 <https://spec.openapis.org/oas/latest.html#tag-object>`_ 相关的字符串列表。

``security``
    与 `security requirements 规范 <https://spec.openapis.org/oas/latest.html#securityRequirementObject>`_ 
    相关的字典列表。

``summary``
    用于路由 schema *summary* 部分的文本。

``description``
    用于路由 schema *description* 部分的文本。

``response_description``
    用于路由响应 schema *description* 部分的文本。

``operation_class``
    :class:`Operation <.openapi.spec.operation.Operation>` 的子类，
    可用于完全自定义处理器的 `operation object <https://spec.openapis.org/oas/v3.1.0#operation-object>`_。

``operation_id``
    返回字符串的字符串或可调用对象，用作路由 schema *operationId* 的标识符。

``deprecated``
    一个布尔值，指示是否应在 OpenAPI schema 中将此路由标记为已弃用。默认为 ``False``。

``raises``
    从 ``litestar.HttpException`` 扩展的异常类列表。此列表应描述路由处理器函数/方法中引发的所有异常。
    如果涉及任何验证（例如在方法/函数中指定了参数），Litestar ``ValidationException`` 将自动添加到 schema 中。
    对于自定义异常，应定义 `detail` 类属性，该属性将集成到 OpenAPI schema 中。
    如果未指定 `detail` 且异常的状态代码与 `stdlib 状态代码 <https://docs.python.org/3/library/http.html#http-status-codes>`_ 
    中的某个匹配，将应用通用消息。

``responses``
    附加状态代码及其预期内容描述的字典。预期内容应基于描述其结构的 Pydantic 模型。
    它还可以包括描述和预期的媒体类型。例如：

.. note::

    当函数使用 `HTTPRouteHandler` 和多个 `http_method` 装饰时，`operation_id` 将以方法名称为前缀。
    还将以 `Routers` 和 `Controllers` 中使用的路径字符串为前缀，以确保 id 是唯一的。

.. code-block:: python

   from datetime import datetime
   from typing import Optional

   from pydantic import BaseModel

   from litestar import get
   from litestar.openapi.datastructures import ResponseSpec


   class Item(BaseModel): ...


   class ItemNotFound(BaseModel):
       was_removed: bool
       removed_at: Optional[datetime]


   @get(
       path="/items/{pk:int}",
       responses={
           404: ResponseSpec(
               data_container=ItemNotFound, description="Item was removed or not found"
           )
       },
   )
   def retrieve_item(pk: int) -> Item: ...

您还可以在应用程序的更高级别（例如控制器、路由器或应用实例本身）指定 ``security`` 和 ``tags``。例如：

.. code-block:: python

   from litestar import Litestar, get
   from litestar.openapi import OpenAPIConfig
   from litestar.openapi.spec import Components, SecurityScheme, Tag


   @get(
       "/public",
       tags=["public"],
       security=[{}],  # 此端点标记为具有可选安全性
   )
   def public_path_handler() -> dict[str, str]:
       return {"hello": "world"}


   @get("/other", tags=["internal"], security=[{"apiKey": []}])
   def internal_path_handler() -> None: ...


   app = Litestar(
       route_handlers=[public_path_handler, internal_path_handler],
       openapi_config=OpenAPIConfig(
           title="my api",
           version="1.0.0",
           tags=[
               Tag(name="public", description="此端点供外部用户使用"),
               Tag(name="internal", description="此端点供内部用户使用"),
           ],
           security=[{"BearerToken": []}],
           components=Components(
               security_schemes={
                   "BearerToken": SecurityScheme(
                       type="http",
                       scheme="bearer",
                   )
               },
           ),
       ),
   )


在代码中访问 OpenAPI Schema
----------------------------

OpenAPI schema 在 :class:`Litestar <litestar.app.Litestar>` 应用程序的 init 方法期间生成。
一旦 init 完成，就可以通过 ``app.openapi_schema`` 访问它。因此，您始终可以通过访问请求实例在路由处理器、依赖项等内部访问它：

.. code-block:: python

   from litestar import Request, get


   @get(path="/")
   def my_route_handler(request: Request) -> dict:
       schema = request.app.openapi_schema
       return schema.to_schema()


自定义 Pydantic 模型 Schema
----------------------------

您可以按照 `Pydantic 文档 <https://docs.pydantic.dev/latest/usage/json_schema/>`_ 
中的指南自定义为 pydantic 模型生成的 OpenAPI schema。

此外，您可以通过在模型上设置名为 ``__schema_name__`` 的特殊 dunder 属性来影响 pydantic 模型如何转换为 OpenAPI ``components``：

.. literalinclude:: /examples/openapi/customize_pydantic_model_name.py
    :caption: 自定义 Components 示例
    :language: python


上述代码将生成如下所示的 OpenAPI schema 对象：

.. code-block:: json

   {
       "openapi": "3.1.0",
       "info": {"title": "Litestar API", "version": "1.0.0"},
       "servers": [{"url": "/"}],
       "paths": {
           "/id": {
               "get": {
                   "operationId": "Retrieve Id Handler",
                   "responses": {
                       "200": {
                           "description": "Request fulfilled, document follows",
                           "headers": {},
                           "content": {
                               "application/json": {
                                   "schema": {
                                       "$ref": "#/components/schemas/IdContainer"
                                   }
                               }
                           }
                       }
                   },
                   "deprecated": false
               }
           }
       },
       "components": {
           "schemas": {
               "IdContainer": {
                   "properties": {
                       "id": {"type": "string", "format": "uuid", "title": "Id"}
                   },
                   "type": "object",
                   "required": ["id"],
                   "title": "IdContainer"
               }
           }
       }
   }

.. attention::

   如果您使用多个在 schema 中使用相同名称的 pydantic 模型，
   您需要使用 ``__schema_name__`` dunder 来确保每个模型在 schema 中都有唯一的名称，
   否则 schema components 将是不明确的。


自定义 ``Operation`` 类
-------------------------

您可以通过创建 :class:`Operation <.openapi.spec.operation.Operation>` 的子类来自定义生成的 OpenAPI schema 中用于路径的 
`operation object <https://spec.openapis.org/oas/v3.1.0#operation-object>`_。

当需要手动解析请求数据时，此选项可能会有所帮助，因为 Litestar 默认情况下不知道如何创建 OpenAPI operation 数据。

.. literalinclude:: /examples/openapi/customize_operation_class.py
    :caption: 自定义 Components 示例
    :language: python


上述示例将生成如下所示的 OpenAPI schema 对象：

.. code-block:: json

    {
        "info": { "title": "Litestar API", "version": "1.0.0" },
        "openapi": "3.0.3",
        "servers": [{ "url": "/" }],
        "paths": {
            "/": {
                "post": {
                    "tags": ["ok"],
                    "summary": "Route",
                    "description": "Requires OK, Returns OK",
                    "operationId": "Route",
                    "requestBody": {
                        "content": {
                            "text": {
                                "schema": { "type": "string", "title": "Body", "example": "OK" }
                            }
                        },
                        "description": "OK is the only accepted value",
                        "required": false
                    },
                    "responses": {
                        "201": {
                            "description": "Document created, URL follows",
                            "headers": {}
                        }
                    },
                    "deprecated": false,
                    "x-codeSamples": [
                        {
                            "lang": "Python",
                            "source": "import requests; requests.get('localhost/example')",
                            "label": "Python"
                        },
                        {
                            "lang": "cURL",
                            "source": "curl -XGET localhost/example",
                            "label": "curl"
                        }
                    ]
                }
            }
        },
        "components": { "schemas": {} }
    }

.. attention::

   OpenAPI Vendor Extension 字段需要以 `x-` 开头，不应使用默认字段名称转换器处理。
   为解决此问题，Litestar 将在生成 schema 中的字段名称时遵循提供给 
   `dataclass.field <https://docs.python.org/3/library/dataclasses.html#dataclasses.field>`_ 
   元数据的 `alias` 字段。


生成示例
--------

Litestar 可以自动为 schema 的 ``example`` 部分生成示例。
要启用此功能，您需要安装 `polyfactory <https://polyfactory.litestar.dev/>`_ 库，
它作为包额外包含在 ``litestar[polyfactory]`` 和 ``litestar[full]`` 中。

安装后，您可以通过 OpenAPI config 启用示例生成：

.. literalinclude:: /examples/openapi/customize_pydantic_model_name.py
    :language: python
