import sys
import warnings

import pytest

deprecated_imports_names = {"TestClient", "create_test_client", "create_test_request"}


def test_testing_import_deprecation() -> None:
    del sys.modules["starlite"]
    del sys.modules["starlite.testing"]
    del sys.modules["requests"]
    del sys.modules["requests.models"]

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


def test_star_import_doesnt_import_testing() -> None:
    import starlite

    assert set(starlite.__all__) & deprecated_imports_names == set()
