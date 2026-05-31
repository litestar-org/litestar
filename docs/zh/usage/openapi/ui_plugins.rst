------------------
OpenAPI UI 插件
------------------

.. versionadded:: 2.8.0

OpenAPI UI 插件旨在方便与您选择的 OpenAPI UI 框架集成。这些插件有助于创建交互式、用户友好的 API 文档，
使开发人员和最终用户更容易理解和与您的 API 交互。

Litestar 维护并提供了一系列流行的 OpenAPI 文档工具的 UI 插件：

- `Scalar <https://github.com/scalar/scalar/>`_
- `RapiDoc <https://rapidocweb.com/>`_
- `ReDoc <https://redocly.com/>`_
- `Stoplight Elements <https://stoplight.io/open-source/elements>`_
- `Swagger UI <https://swagger.io/tools/swagger-ui/>`_
- `YAML <https://yaml.org/>`_

每个插件都易于配置，允许开发人员自定义版本、路径、CSS 和 JavaScript 资源等方面。


使用 OpenAPI UI 插件
--------------------

使用 OpenAPI UI 插件非常简单，只需导入插件、实例化它并将其添加到 OpenAPIConfig。

.. tab-set::

    .. tab-item:: scalar
        :sync: scalar

        .. literalinclude:: /examples/openapi/plugins/scalar_simple.py
            :language: python

    .. tab-item:: rapidoc
        :sync: rapidoc

        .. literalinclude:: /examples/openapi/plugins/rapidoc_simple.py
            :language: python

    .. tab-item:: redoc
        :sync: redoc

        .. literalinclude:: /examples/openapi/plugins/redoc_simple.py
            :language: python

    .. tab-item:: stoplight
        :sync: stoplight

        .. literalinclude:: /examples/openapi/plugins/stoplight_simple.py
            :language: python

    .. tab-item:: swagger
        :sync: swagger

        .. literalinclude:: /examples/openapi/plugins/swagger_ui_simple.py
            :language: python

    .. tab-item:: yaml
        :sync: yaml

        .. literalinclude:: /examples/openapi/plugins/yaml_simple.py
            :language: python

        .. tip::
            渲染 YAML 需要 `PyYAML <https://pyyaml.org/wiki/PyYAMLDocumentation>`_ 库，
            可以通过 ``litestar[yaml]`` 包额外安装

    .. tab-item:: multiple

        .. literalinclude:: /examples/openapi/plugins/serving_multiple_uis.py
            :caption: 可以同时提供任意组合的 UI。
            :language: python


配置 OpenAPI UI 插件
---------------------

每个插件都可以通过在实例化时传递选项来定制以满足您的独特需求。
有关每个插件选项的完整详细信息，请参阅 :doc:`API 参考 </reference/openapi/plugins>`。

所有插件都支持：

- ``path``：每个插件都有自己的默认值，例如 RapiDoc 的 ``/rapidoc``。可以覆盖此设置以在不同路径提供 UI。
- ``media_type``：插件的默认媒体类型，通常默认为 ``text/html``。
- ``favicon``：应该是有效的 ``<link>`` 标签的字符串，例如 ``<link rel="icon" href="https://example.com/favicon.ico">``。
- ``style``：应该是有效的 ``<style>`` 标签的字符串，例如 ``<style>body { margin: 0; padding: 0; }</style>``。

大多数插件支持以下附加选项：

- ``version``：要使用的 UI 的 JS 和（在某些情况下）CSS 包的版本。我们使用 ``version`` 来构造从 ``unpkg`` 检索包的 URL，例如 ``https://unpkg.com/rapidoc@<version>/dist/rapidoc-min.js``
- ``js_url``：JS 包的 URL。如果提供，这将覆盖 ``version`` 选项。
- ``css_url``：CSS 包的 URL。如果提供，这将覆盖 ``version`` 选项。

以下是一些插件配置示例：

.. tab-set::

    .. tab-item:: scalar
        :sync: scalar

        .. literalinclude:: /examples/openapi/plugins/scalar_config.py
            :language: python

    .. tab-item:: rapidoc
        :sync: rapidoc

        .. literalinclude:: /examples/openapi/plugins/rapidoc_config.py
            :language: python

    .. tab-item:: redoc
        :sync: redoc

        .. literalinclude:: /examples/openapi/plugins/redoc_config.py
            :language: python

    .. tab-item:: stoplight
        :sync: stoplight

        .. literalinclude:: /examples/openapi/plugins/stoplight_config.py
            :language: python

    .. tab-item:: swagger
        :sync: swagger

        .. literalinclude:: /examples/openapi/plugins/swagger_ui_config.py
            :language: python

配置 OpenAPI 根路径
--------------------

OpenAPI 根路径是提供 OpenAPI 表示的路径。默认情况下，这是 ``/schema``。
可以通过设置 :attr:`OpenAPIConfig.path` 属性来更改此设置。

在以下示例中，我们将 OpenAPI 根路径配置为 ``/docs``：

.. literalinclude:: /examples/openapi/customize_path.py
    :language: python

这将导致任何 OpenAPI 端点在 ``/docs`` 而不是 ``/schema`` 提供，例如 ``/docs/openapi.json``。

构建您自己的 OpenAPI UI 插件
-----------------------------

如果 Litestar 没有为您选择的 OpenAPI UI 框架提供内置支持，
您可以通过子类化 :class:`OpenAPIRenderPlugin` 并实现 :meth:`OpenAPIRenderPlugin.render` 方法来轻松创建自己的插件。

为了演示构建自定义插件，我们将查看一个与 Litestar 维护的 :class:`ScalarRenderPlugin` 非常相似的插件。这是成品：

.. literalinclude:: /examples/openapi/plugins/custom_plugin.py
    :language: python

类定义
~~~~~~

类 ``ScalarRenderPlugin`` 继承自 :class:`OpenAPIRenderPlugin`：

.. literalinclude:: /examples/openapi/plugins/custom_plugin.py
    :language: python
    :lines: 10

``__init__`` 构造函数
~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/openapi/plugins/custom_plugin.py
    :language: python
    :lines: 11-22

我们通过以下参数支持配置：

- ``version``：指定要使用的 RapiDoc 版本。
- ``js_url``：RapiDoc JavaScript 包的自定义 URL。
- ``css_url``：RapiDoc CSS 包的自定义 URL。
- ``path``：RapiDoc UI 将被提供的 URL 路径。
- ``**kwargs``：捕获要传递给超类的附加参数。

如果未提供，我们为 Scalar JavaScript 包构造一个 url：

.. literalinclude:: /examples/openapi/plugins/custom_plugin.py
    :language: python
    :lines: 20

``render()``
~~~~~~~~~~~~

.. literalinclude:: /examples/openapi/plugins/custom_plugin.py
    :language: python
    :lines: 24

最后，我们定义 ``render`` 方法，它由 Litestar 调用以渲染 UI。它接收一个 :class:`Request` 对象和 ``openapi_schema`` 作为字典。

在 ``render`` 方法内部，我们构造 HTML 以渲染 UI，并将其作为字符串返回。

- ``head``：定义 HTML ``<head>`` 部分，包括来自 ``openapi_schema`` 的标题、任何附加样式（``self.style``）、favicon 和自定义样式表（如果提供）：

  .. literalinclude:: /examples/openapi/plugins/custom_plugin.py
    :language: python
    :lines: 25-35

- ``body``：构造 HTML ``<body>``，包括指向 OpenAPI JSON 的链接和 JavaScript 包：

  .. literalinclude:: /examples/openapi/plugins/custom_plugin.py
    :language: python
    :lines: 37-43

- 最后，返回完整的 HTML 文档（作为字节字符串），组合 head 和 body。

  .. literalinclude:: /examples/openapi/plugins/custom_plugin.py
    :language: python
    :lines: 45-51

与 ``Router`` 交互
------------------

:class:`Router` 的实例用于提供 OpenAPI 端点，并通过 :meth:`OpenAPIRenderPlugin.receive_router` 方法对插件可用。

这可以用于多种目的，包括向 ``Router`` 添加附加路由。

.. literalinclude:: /examples/openapi/plugins/receive_router.py
    :language: python

Swagger UI 中的 OAuth2
-----------------------

使用 Swagger 时，可以通过 :meth:`SwaggerRenderPlugin <litestar.openapi.plugins.SwaggerRenderPlugin.__init__>` 的 :paramref:`~.openapi.plugins.SwaggerRenderPlugin.init_oauth` 参数配置 OAuth2 设置，该参数可以设置为包含 Swagger UI 文档中描述的 OAuth2 参数的字典，`这里 <https://swagger.io/docs/open-source-tools/swagger-ui/usage/oauth2/>`_。

这样，您可以预设您的 clientId 或启用 PKCE 支持。

.. literalinclude:: /examples/openapi/plugins/swagger_ui_oauth.py
    :language: python

自定义 OpenAPI UI
-----------------

可以通过覆盖渲染插件类上的默认 ``css_url`` 和 ``js_url`` 属性来自定义 OpenAPI UI 的样式和行为，例如：

.. literalinclude:: /examples/openapi/plugins/scalar_customized.py
    :language: python

要了解有关自定义 ``Scalar`` UI 的更多信息，请参阅 `Scalar 文档 <https://docs.scalar.com/>`_。

CDN 和离线文件支持
------------------

每个插件都支持 ``js_url`` 和 ``css_url`` 属性，可用于指定 JavaScript 的自定义 URL。
这些可用于从 CDN 提供 JavaScript 和 CSS，或从本地目录提供文件。
