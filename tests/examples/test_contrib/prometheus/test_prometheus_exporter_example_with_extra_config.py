from typing import Any, Dict

from prometheus_client import REGISTRY

from litestar import get
from litestar.contrib.prometheus import PrometheusMiddleware
from litestar.status_codes import HTTP_200_OK
from litestar.testing import TestClient


def clear_collectors() -> None:
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        REGISTRY.unregister(collector)

    PrometheusMiddleware._metrics = {}


def test_prometheus_exporter_with_extra_config_example() -> None:
    from docs.examples.contrib.prometheus.using_prometheus_exporter_with_extra_configs import app

    clear_collectors()

    @get("/test")
    def home() -> Dict[str, Any]:
        return {"hello": "world"}

    app.register(home)

    with TestClient(app) as client:
        client.get("/home")
        metrix_exporter_response = client.get("/custom-path")

        assert metrix_exporter_response.status_code == HTTP_200_OK
        metrics = metrix_exporter_response.content.decode()

        assert (
            """litestar_requests_in_progress{app_name="litestar-example",location="earth",method="GET",path="/custom-path",status_code="200",version_no="v2.0"} 1.0"""
            in metrics
        )
