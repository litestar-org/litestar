:orphan:

3.x 更新日志
=============

.. changelog:: 3.0.0
    :date: 2024-08-30

    .. change:: 移除所有 SQLAlchemy 模块，改为直接使用 advanced-alchemy 导入
        :type: 新功能
        :breaking:
        :pr: TBD

        移除 Litestar 中所有 SQLAlchemy 功能。`litestar.contrib.sqlalchemy` 和 `litestar.plugins.sqlalchemy` 模块已完全移除。用户现在必须直接从 `advanced_alchemy.extensions.litestar` 导入。

        迁移方式：
        - `from litestar.contrib.sqlalchemy import X` → `from advanced_alchemy.extensions.litestar import X`
        - `from litestar.plugins.sqlalchemy import Y` → `from advanced_alchemy.extensions.litestar import Y`

        这完成了关注点分离，advanced-alchemy 成为 Litestar SQLAlchemy 集成的唯一提供者。

    .. change:: 移除弃用的 `litestar.contrib.prometheus` 模块
        :type: 新功能
        :breaking:
        :pr: 4328
        :issue: 4305

        移除弃用的 `litestar.contrib.prometheus` 模块。仍在使用该模块的代码应切换到 `litestar.plugins.prometheus`。

    .. change:: `AsyncTestClient` 改为原生异步
        :type: 新功能
        :pr: 4291
        :issue: 1920
        :breaking:

        重新实现 :class:`~litestar.testing.AsyncTestClient`，使其原生异步，即使用当前运行的事件循环运行应用，而不是在新线程中运行单独的事件循环。新增 :class:`~litestar.testing.AsyncWebSocketTestSession`，为 WebSocket 提供异步测试工具。

        为确保 `TestClient` 和 `AsyncTestClient` 行为一致，所有测试工具均重写为异步优先，同步版本内部代理到异步实现，并在专用线程+事件循环中运行。

        .. seealso::
            :ref:`usage/testing:测试客户端`
            :ref:`usage/testing:如何选择测试客户端`

    .. change:: 移除 Litestar 的弃用插件属性
        :type: 新功能
        :pr: 4297
        :breaking:

        移除 :class:`Litestar` 的所有弃用 `<plugin_type>_plugins` 属性。

        ===================================  ===================================
        已移除                              替代方案
        ===================================  ===================================
        `Litestar.openapi_schema_plugins`  `Litestar.plugins.openapi_schema`
        `Litestar.cli_plugins`             `Litestar.plugins.cli`
        `Litestar.serialization_plugins`   `Litestar.serialization.cli`
        ===================================  ===================================

    .. change:: 移除弃用的 `allow_reserved` 和 `allow_empty_value` 属性
        :type: 新功能
        :pr: 4299
        :breaking:

        从 :class:`~litestar.datastructures.ResponseHeader` 和 :class:`~litestar.openapi.spec.OpenAPIHeader` 移除弃用的 `allow_reserved` 和 `allow_empty_value` 属性。

    .. change:: 移除弃用的 `traceback_line_limit` 参数
        :type: 新功能
        :breaking:
        :pr: 4300

        移除 :class:`~litestar.logging.config.LoggingConfig` 的 `traceback_line_limit` 参数。自 2.9.0 起该参数已无效，可安全移除。

    .. change:: 移除弃用的 `litestar.middleware.cors` 模块
        :type: 新功能
        :breaking:
        :pr: 4309

        移除弃用的 `litestar.middleware.cors` 模块和 `litestar.middleware.cors.CORSMiddleware`。请使用 :class:`~litestar.config.cors.CORSConfig` 配置 CORS 中间件。

    .. change:: 移除 ASGI 响应类和 `to_asgi_response` 方法的弃用参数 `encoded_headers`
        :type: 新功能
        :pr: 4311
        :breaking:

        从以下类中移除弃用的 `encoded_headers` 参数：

        - :class:`~litestar.response.base.ASGIResponse`
        - :meth:`~litestar.response.Response.to_asgi_response`
        - :class:`~litestar.response.file.ASGIFileResponse`
        - :meth:`~litestar.response.File.to_asgi_response`
        - :class:`~litestar.response.redirect.ASGIRedirectResponse`
        - :meth:`~litestar.response.Redirect.to_asgi_response`
        - :class:`~litestar.response.streaming.ASGIStreamingResponse`
        - :meth:`~litestar.response.Stream.to_asgi_response`
        - :meth:`~litestar.response.Template.to_asgi_response`

        仍在使用 `encoded_headers` 的代码应迁移到使用 `headers` 参数。

    .. change:: 移除弃用的 `litestar.contrib.htmx` 模块
        :type: 新功能
        :breaking:
        :pr: 4316
        :issue: 4303

        移除弃用的 `litestar.contrib.htmx` 模块。仍在使用该模块的代码应切换到 `litestar_htmx`。

        通过 ``litestar[htmx]`` 额外项安装。

    .. change:: 移除弃用的 `LitestarType`
        :type: 新功能
        :pr: 4312
        :breaking:

        移除弃用的 `litestar.types.internal_types.LitestarType` 类型别名。请使用 ``type[Litestar]``。

    .. change:: 移除弃用的 `TemplateContext`
        :type: 新功能
        :pr: 4313
        :breaking:

        移除弃用的 `litestar.template.base.TemplateContext` 类型。应该使用 :class:`collections.abc.Mapping` 替代。

    .. change:: 移除弃用的 `ASGIResponse.encoded_headers` 属性
        :type: 新功能
        :pr: 4314
        :breaking:

        移除弃用的 `ASGIResponse.encoded_headers` 属性。应使用 :meth:`~litestar.response.base.ASGIResponse.encode_headers`。

    .. change:: 移除弃用的 `pydantic_get_unwrapped_annotation_and_type_hints`
        :type: 新功能
        :pr: 4315
        :breaking:

        移除弃用的 `pydantic_get_unwrapped_annotation_and_type_hints` 函数。

    .. change:: 移除弃用的 `litestar.contrib.attrs` 模块
        :type: 新功能
        :breaking:
        :pr: 4322
        :issue: 4302

        移除弃用的 `litestar.contrib.attrs` 模块。仍在使用该模块的代码应切换到 `litestar.plugins.attrs`。

    .. change:: 移除弃用的 `litestar.contrib.jwt` 模块
        :type: 新功能
        :breaking:
        :pr: 4333
        :issue: 4304

        移除弃用的 `litestar.contrib.jwt` 模块。仍在使用该模块的代码应切换到 `litestar.security.jwt`。

    .. change:: 移除弃用的 `litestar.contrib.repository` 模块
        :type: 新功能
        :breaking:
        :pr: 4337
        :issue: 4307

        移除弃用的 `litestar.contrib.repository` 模块。仍在使用该模块的代码应切换到 `litestar.repository`。

    .. change:: 移除弃用的 `litestar.contrib.pydantic` 模块
        :type: 新功能
        :breaking:
        :pr: 4339
        :issue: 4306

        移除弃用的 `litestar.contrib.pydantic` 模块。仍在使用该模块的代码应切换到 `litestar.plugins.pydantic`。

    .. change:: 移除弃用的模块 `litestar/contrib/minijnja`
        :type: 新功能
        :breaking:
        :pr: 4357
        :issue: 4357

        移除弃用的模块 `litestar.contrib.minijnja`。该模块创建时名称拼写错误（`minijnja` 而非 `minijinja`）。应使用 `litestar.contrib.minijinja`。

    .. change:: 为 `PydanticPlugin` 添加 `round_trip` 参数
        :type: 新功能
        :pr: 4350
        :issue: 4349

        :class:`~litestar.contrib.pydantic.PydanticPlugin` 新增 ``round_trip: bool`` 参数，允许正确序列化 ``pydanctic.Json`` 等类型。

    .. change:: 移除弃用的 `litestar.contrib.minijinja.minijinja_from_state` 函数
        :type: 新功能
        :breaking:
        :pr: 4355
        :issue: 4356

        移除弃用的 `litestar.contrib.minijinja.minijinja_from_state` 函数。应使用接收 minijinja `State` 对象作为第一个参数的可调用对象。

    .. change:: 移除弃用的 `litestar.contrib.piccolo` 模块
        :type: 新功能
        :breaking:
        :pr: 4363
        :issue: 4364

        使用 ``litestar[piccolo]`` 额外安装目标和 ``litestar_piccolo`` 插件：
        https://github.com/litestar-org/litestar-piccolo

    .. change:: 将带 `default_factory` 的 pydantic 字段从 `Optional` 改为 `NotRequired`
        :type: 错误修复
        :pr: 4347
        :issue: 4294

        现在，在 OpenAPI 模式中，带 `default_factory` 的 `pydantic` 字段显示为非空且不必需。以前，这些字段是可为空且不必需的。

    .. change:: 零成本排除中间件
        :type: 新功能
        :breaking:

        继承自 :class:`~litestar.middleware.base.ASGIMiddleware` 的中间件，在通过 ``scope`` 或 ``exclude_opt_key`` 选项排除时，现在具有零运行时成本。

        以前，基础中间件总是为每个请求调用，评估排除条件，然后调用用户定义的中间件函数。如果中间件定义了 ``scopes = (ScopeType.HTTP,)``，它仍会为*每个*请求调用，无论作用域类型如何。只有对于 ``HTTP`` 类型的请求，它才会调用用户的函数。

        .. note::
            此行为对于传统的 ``AbstractMiddleware`` 仍然适用

        通过*零成本排除*，排除是静态评估的。在应用创建时，当路由处理器注册并构建其中间件栈时，要排除的中间件将不会包含在栈中。

        .. note::
            尽管此更改标记为破坏性，但预计不会出现运行时行为差异。但某些测试用例可能会中断，如果它们依赖于 ``ASGIMiddleware`` 创建的中间件包装器总是被调用这一事实

    .. change:: 支持类型化字典模式中的 `typing.ReadOnly`
        :type: 新功能
        :issue: 4423
        :pr: 4424

        支持在如下模式中解包 ``ReadOnly`` 类型：

        .. code:: python

          from typing import ReadOnly, TypedDict

          class User(TypedDict):
              id: ReadOnly[int]

        对于 python 版本 <3.13，应使用 ``typing_extensions.ReadOnly``。


    .. change:: 向 `ASGIMiddleware` 添加 `should_bypass_for_scope` 以允许动态排除中间件
        :type: 新功能
        :pr: 4441

        添加新属性 :attr:`~litestar.middleware.ASGIMiddleware.should_bypass_for_scope`；这是一个可调用对象，接收 :class:`~litestar.types.Scope` 并返回布尔值，指示是否对当前请求绕过中间件。
