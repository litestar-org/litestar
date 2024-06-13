from litestar import Litestar
from litestar.contrib.prometheus import PrometheusConfig, PrometheusController


def create_app(group_path: bool = False):
    # Default app name and prefix is litestar.
    prometheus_config = PrometheusConfig(group_path=group_path)

    # By default the metrics are available in prometheus format and the path is set to '/metrics'.
    # If you want to change the path and format you can do it by subclassing the PrometheusController class.

    # Creating the litestar app instance with our custom PrometheusConfig and PrometheusController.
    return Litestar(route_handlers=[PrometheusController], middleware=[prometheus_config.middleware])
