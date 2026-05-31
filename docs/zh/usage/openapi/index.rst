OpenAPI
=======

Litestar 具有一流的 OpenAPI 支持，提供以下功能：

- 自动生成 `OpenAPI 3.1.0 Schema <https://spec.openapis.org/oas/v3.1.0>`_，可作为 YAML 和 JSON 提供。
- 使用多个不同库内置支持静态文档站点生成。
- 使用预定义的类型安全数据类进行完整配置。


Litestar 包含使用 Python 数据类实现的 `最新版本的 OpenAPI 规范 <https://spec.openapis.org/oas/latest.html>`_ 的完整实现。此实现用作生成 OpenAPI 规范的基础，支持 :func:`~dataclasses.dataclass`、:class:`~typing.TypedDict`，以及 Pydantic 和 msgspec 模型，以及任何实现了 :ref:`插件 <plugins>` 的第三方实体。

这也是高度可配置的 - 用户可以以多种方式自定义 OpenAPI 规范 - 从全局传递配置到在路由处理程序装饰器上设置 :ref:`特定 kwargs <usage/openapi/schema_generation:Configuring schema generation on a route handler>`。

.. toctree::

    schema_generation
    ui_plugins
