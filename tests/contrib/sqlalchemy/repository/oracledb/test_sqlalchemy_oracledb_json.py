"""Unit tests for the SQLAlchemy Repository implementation for psycopg."""
from __future__ import annotations

import platform
import sys

import pytest
from sqlalchemy import Engine, NullPool, create_engine
from sqlalchemy.dialects import oracle

from tests.contrib.sqlalchemy.models_uuid import (
    UUIDEventLog,
)

pytestmark = [
    pytest.mark.skipif(sys.platform != "linux", reason="docker not available on this platform"),
    pytest.mark.skipif(platform.uname()[4] != "x86_64", reason="oracle not available on this platform"),
    pytest.mark.usefixtures("oracle_service"),
]


@pytest.mark.sqlalchemy_oracledb
@pytest.fixture(name="engine")
def fx_engine(docker_ip: str) -> Engine:
    """Postgresql instance for end-to-end testing.

    Args:
        docker_ip: IP address for TCP connection to Docker containers.

    Returns:
        Async SQLAlchemy engine instance.
    """
    return create_engine(
        "oracle+oracledb://:@",
        thick_mode=False,
        connect_args={
            "user": "app",
            "password": "super-secret",
            "host": docker_ip,
            "port": 1512,
            "service_name": "xepdb1",
            "encoding": "UTF-8",
            "nencoding": "UTF-8",
        },
        echo=True,
        poolclass=NullPool,
    )


@pytest.mark.xfail
def test_json_constraint_generation(engine: Engine) -> None:
    _ddl = UUIDEventLog.__table__.compile(engine, dialect=oracle.dialect())  # type: ignore
    assert "BLOB" in str(_ddl)
