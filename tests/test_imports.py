import subprocess
import sys
import warnings

import pytest

deprecated_imports_names = {"TestClient", "create_test_client", "create_test_request"}


@pytest.mark.skipif("starlite" in sys.modules, reason="This tests expects starlite to be imported for the first time")
def test_testing_import_deprecation() -> None:
    import starlite

    assert deprecated_imports_names & starlite.__dict__.keys() == set()
    assert "starlite.testing" not in sys.modules
    assert "requests" not in sys.modules
    assert "requests.models" not in sys.modules

    imported_values = {}
    for dynamic_import_name in deprecated_imports_names:
        with pytest.warns(DeprecationWarning):
            imported_values[dynamic_import_name] = getattr(starlite, dynamic_import_name)

    assert deprecated_imports_names & starlite.__dict__.keys() == deprecated_imports_names
    assert "starlite.testing" in sys.modules
    assert "requests.models" in sys.modules

    # ensure no warnings emitted on the second usage
    with warnings.catch_warnings(record=True) as record:
        for deprecated_name in deprecated_imports_names:
            getattr(starlite, deprecated_name)

    assert record == []
    from starlite import testing

    assert imported_values == {
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


def test_star_import_doesnt_import_testing() -> None:
    import starlite

    assert set(starlite.__all__) & deprecated_imports_names == set()
