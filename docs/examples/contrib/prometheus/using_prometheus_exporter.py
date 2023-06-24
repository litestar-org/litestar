from litestar import Litestar
from litestar.contrib.prometheus import PrometheusConfig, PrometheusController

# We need to create a instance of PrometheusConfig with extra options if you want.
# Default app name and prefix is litestar, rest all other options are None.
prometheus_config = PrometheusConfig()


# By default the metric are available in prometheus format and the path is /metrics.
# If you want to change the path and format you can do it by inheriting the PrometheusController class

# Creating the litestar app instance with our custom PrometheusConfig and PrometheusController.
app = Litestar(route_handlers=[PrometheusController], middleware=[prometheus_config.middleware])
