==========
Prometheus
==========

Litestar 包含从 ``litestar.plugins.prometheus`` 导出的可选 Prometheus 导出器。
要使用此包，您应首先安装所需的依赖项：

.. code-block:: bash
    :caption: 作为单独的包

    pip install prometheus-client


.. code-block:: bash
    :caption: 作为 Litestar 额外包

    pip install 'litestar[prometheus]'

满足这些要求后，您可以检测您的 Litestar 应用程序：

.. literalinclude:: /examples/plugins/prometheus/using_prometheus_exporter.py
    :language: python
    :caption: 使用 Prometheus 导出器

您还可以自定义配置：

.. literalinclude:: /examples/plugins/prometheus/using_prometheus_exporter_with_extra_configs.py
    :language: python
    :caption: 配置 Prometheus 导出器
