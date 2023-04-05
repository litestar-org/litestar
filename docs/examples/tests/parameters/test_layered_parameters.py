from typing import Any, Dict

import pytest

from examples.parameters.layered_parameters import app
from starlite.testing import TestClient


@pytest.mark.parametrize(
    "params,status_code,expected",
    [
        (
            {
                "headers": {"MyHeader": "foo"},
                "cookies": {"special-cookie": "bar"},
                "params": {"controller_param": "11", "local_param": "foo"},
            },
            200,
            {"controller_param": 11, "local_param": "foo", "path_param": 11, "router_param": "foo"},
        ),
        (
            {
                "cookies": {"special-cookie": "bar"},
                "params": {"controller_param": "11", "local_param": "foo"},
            },
            400,
            None,
        ),
        (
            {
                "headers": {"MyHeader": "foo"},
                "cookies": {"special-cookie": "bar"},
                "params": {"controller_param": "11"},
            },
            400,
            None,
        ),
        (
            {
                "headers": {"MyHeader": "foo"},
                "cookies": {"special-cookie": "bar"},
                "params": {"local_param": "foo"},
            },
            400,
            None,
        ),
    ],
)
def test_layered_parameters(params: Dict[str, Any], status_code: int, expected: Dict[str, Any]) -> None:
    with TestClient(app=app) as client:
        client.cookies = params.pop("cookies")
        res = client.get("/router/controller/11", **params)
        assert res.status_code == status_code, res.json()
        if expected:
            assert res.json() == expected
