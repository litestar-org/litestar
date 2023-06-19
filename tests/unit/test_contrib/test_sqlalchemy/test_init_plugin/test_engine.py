from __future__ import annotations

from litestar.contrib.sqlalchemy.plugins.init.config.engine import serializer


def test_serializer_returns_string() -> None:
    """Test that serializer returns a string."""
    assert isinstance(serializer({"a": "b"}), str)
