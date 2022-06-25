import subprocess
import sys

import pytest


@pytest.mark.skipif("starlite" in sys.modules, reason="This tests expects starlite to be imported for the first time")
def test_testing_import_deprecation() -> None:
    import starlite

    dynamic_imports_names = {"TestClient", "create_test_client", "create_test_request"}
    assert dynamic_imports_names & starlite.__dict__.keys() == set()
    assert "starlite.testing" not in sys.modules
    assert "requests" not in sys.modules
    assert "requests.models" not in sys.modules

    dynamic_imports = {}
    for dynamic_import_name in dynamic_imports_names:
        dynamic_imports[dynamic_import_name] = getattr(starlite, dynamic_import_name)

    assert dynamic_imports_names & starlite.__dict__.keys() == dynamic_imports_names
    assert "starlite.testing" in sys.modules
    assert "requests.models" in sys.modules

    from starlite import testing

    assert dynamic_imports == {
        "TestClient": testing.TestClient,
        "create_test_client": testing.create_test_client,
        "create_test_request": testing.create_test_request,
    }


@pytest.mark.skipif(
    "starlite" not in sys.modules, reason="Was able to run previous test, no need to launch subprocess for that"
)
def test_testing_import_deprecation_in_subprocess() -> None:
    """Run test_testing_import_deprecation in subprocess so it can test importing starlite for the first time"""
    subprocess.check_call(
        [sys.executable, "-m", "pytest", f"{__file__}::{test_testing_import_deprecation.__name__}"], timeout=5
    )
