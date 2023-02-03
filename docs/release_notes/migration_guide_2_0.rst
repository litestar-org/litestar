Migrating to Starlite 2.0
=========================


Changed import paths
---------------------

+----------------------------------------------+------------------------------------------------------------------+
| ``1.50``                                     | ``2.x``                                                          |
+==============================================+==================================================================+
| ``from starlite import BackgroundTask``      | ``from starlite.background_tasks import BackgroundTask``         |
+----------------------------------------------+------------------------------------------------------------------+
| ``from starlite import BackgroundTasks``     | ``from starlite.background_tasks import BackgroundTasks``        |
+----------------------------------------------+------------------------------------------------------------------+
| **Configuration**                                                                                               |
+----------------------------------------------+------------------------------------------------------------------+
| ``from starlite import AllowedHostsConfig``  | ``from starlite.config.allowed_hosts import AllowedHostsConfig`` |
+----------------------------------------------+------------------------------------------------------------------+
| ``from starlite import BaseLoggingConfig``   | ``from starlite.config.logging import BaseLoggingConfig``        |
+----------------------------------------------+------------------------------------------------------------------+
| ``from starlite import CacheConfig``         | ``from starlite.config.cache import CacheConfig``                |
+----------------------------------------------+------------------------------------------------------------------+
| ``from starlite import CompressionConfig``   | ``from starlite.config.compression import CompressionConfig``    |
+----------------------------------------------+------------------------------------------------------------------+
| ``from starlite import CORSConfig``          | ``from starlite.config.cors import CORSConfig``                  |
+----------------------------------------------+------------------------------------------------------------------+
| ``from starlite import CSRFConfig``          | ``from starlite.config.csrf import CSRFConfig``                  |
+----------------------------------------------+------------------------------------------------------------------+
| ``from starlite import LoggingConfig``       | ``from starlite.config.logging import LoggingConfig``            |
+----------------------------------------------+------------------------------------------------------------------+
| ``from starlite import StructLoggingConfig`` | ``from starlite.config.logging import StructLoggingConfig``      |
+----------------------------------------------+------------------------------------------------------------------+
| ``from starlite import OpenAPIConfig``       | ``from starlite.config.openapi import OpenAPIConfig``            |
+----------------------------------------------+------------------------------------------------------------------+
| ``from starlite import StaticFilesConfig``   | ``from starlite.config.static_files import StaticFilesConfig``   |
+----------------------------------------------+------------------------------------------------------------------+
| ``from starlite import TemplateConfig``      | ``from starlite.config.templates import TemplateConfig``         |
+----------------------------------------------+------------------------------------------------------------------+
