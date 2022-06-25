import subprocess
import sys
import warnings

import pytest


@pytest.mark.skipif("starlite" in sys.modules, reason="This tests expects starlite to be imported for the first time")
def test_testing_import_deprecation() -> None:
    import starlite

    deprecated_imports = {"TestClient", "create_test_client", "create_test_request"}
    assert deprecated_imports & starlite.__dict__.keys() == set()
    assert "starlite.testing" not in sys.modules
    assert "requests" not in sys.modules
    assert "requests.models" not in sys.modules

    for deprecated_name in deprecated_imports:
        with pytest.warns(DeprecationWarning):
            getattr(starlite, deprecated_name)

    assert deprecated_imports & starlite.__dict__.keys() == deprecated_imports
    assert "starlite.testing" in sys.modules
    assert "requests.models" in sys.modules

    # ensure no warnings emited on the second usage
    with warnings.catch_warnings(record=True) as record:
        for deprecated_name in deprecated_imports:
            getattr(starlite, deprecated_name)

    assert record == []


@pytest.mark.skipif(
    "starlite" not in sys.modules, reason="Was able to run previous test, no need to launch subprocess for that"
)
def test_testing_import_deprecation_in_subprocess() -> None:
    """Run test_testing_import_deprecation in subprocess so it can test importing starlite for the first time"""
    subprocess.check_call(
        [sys.executable, "-m", "pytest", f"{__file__}::{test_testing_import_deprecation.__name__}"], timeout=1
    )
