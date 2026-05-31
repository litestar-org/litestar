=============
OpenTelemetry
=============

Litestar 包含从 ``litestar.contrib.opentelemetry`` 导出的可选 OpenTelemetry 检测。
要使用此包，您应首先安装所需的依赖项：

.. code-block:: bash
    :caption: 作为单独的包

    pip install opentelemetry-instrumentation-asgi


.. code-block:: bash
    :caption: 作为 Litestar 额外包

    pip install 'litestar[opentelemetry]'

满足这些要求后，您可以通过创建 
:class:`OpenTelemetryConfig <litestar.contrib.opentelemetry.OpenTelemetryConfig>` 的实例
并将其创建的中间件传递给 Litestar 构造函数来检测您的 Litestar 应用程序：

.. code-block:: python

   from litestar import Litestar
   from litestar.contrib.opentelemetry import OpenTelemetryConfig, OpenTelemetryPlugin

   open_telemetry_config = OpenTelemetryConfig()

   app = Litestar(plugins=[OpenTelemetryPlugin(open_telemetry_config)])

如果您配置了全局 ``tracer_provider`` 和/或 ``metric_provider`` 以及使用这些的导出器，
上述示例将开箱即用（有关更多详细信息，请参阅 
`OpenTelemetry Exporter 文档 <https://opentelemetry.io/docs/instrumentation/python/exporters/>`_）。

您还可以将配置传递给 ``OpenTelemetryConfig``，告诉它使用哪些提供程序。
有关您可以使用的配置选项，请参阅 
:class:`参考文档 <litestar.contrib.opentelemetry.OpenTelemetryConfig>`。
