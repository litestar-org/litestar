Prometheus
==========

Litestar includes optional Prometheus exporter that is exported from ``litestar.plugins.prometheus``. To use
this package, you should first install the required dependencies:

.. code-block:: bash
    :caption: as separate package

    pip install prometheus-client


.. code-block:: bash
    :caption: as a Litestar extra

    pip install 'litestar[prometheus]'

Once these requirements are satisfied, you can instrument your Litestar application:

.. literalinclude:: /examples/plugins/prometheus/using_prometheus_exporter.py
    :language: python
    :caption: Using the Prometheus Exporter

You can also customize the configuration:

.. literalinclude:: /examples/plugins/prometheus/using_prometheus_exporter_with_extra_configs.py
    :language: python
    :caption: Configuring the Prometheus Exporter
