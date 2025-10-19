import os

from litestar.utils import envflag


def test_envflag_truthy_values():
    for value in ("1", "true", "TRUE", "t", "T", "yes", "YES", "on", "ON", "y", "Y"):
        os.environ["TEST_FLAG"] = value
        assert envflag("TEST_FLAG") is True
        del os.environ["TEST_FLAG"]


def test_envflag_falsy_values():
    for value in ("0", "false", "no", "off", ""):
        os.environ["TEST_FLAG"] = value
        assert envflag("TEST_FLAG") is False
        del os.environ["TEST_FLAG"]


def test_envflag_missing():
    assert envflag("NONEXISTENT_VAR") is False
