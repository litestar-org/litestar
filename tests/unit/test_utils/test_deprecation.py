from __future__ import annotations

import pytest

from litestar.utils.deprecation import deprecated, warn_deprecation


def test_warn_deprecation() -> None:
    with pytest.warns(
        DeprecationWarning,
        match="Call to deprecated function 'something'. Deprecated in litestar 3. This function will be removed in the next major version",
    ):
        warn_deprecation("3", deprecated_name="something", kind="function")


def test_warn_deprecation_attributes_warning_to_stacklevel_frame() -> None:
    with pytest.warns(DeprecationWarning) as record:
        warn_deprecation("3", deprecated_name="something", kind="function", stacklevel=1)

    assert record[0].filename == warn_deprecation.__code__.co_filename


def test_warn_pending_deprecation() -> None:
    with pytest.warns(
        PendingDeprecationWarning,
        match="Call to function awaiting deprecation 'something'. Deprecated in litestar 3. This function will be removed in the next major version",
    ):
        warn_deprecation("3", deprecated_name="something", kind="function", pending=True)


def test_deprecated() -> None:
    @deprecated("3")
    def foo() -> None:
        pass

    with pytest.warns(
        DeprecationWarning,
        match="Call to deprecated function 'foo'. Deprecated in litestar 3. This function will be removed in the next major version",
    ):
        foo()
