"""Tests for the ``litestar.contrib.mako`` deprecation shim.

The shim must:

* re-export :class:`~litestar.plugins.mako.MakoTemplateEngine` and
  :class:`~litestar.plugins.mako.MakoTemplate` while emitting a
  :class:`DeprecationWarning` on attribute access;
* preserve identity equality with the new module for both symbols;
* stay silent on bare ``import litestar.contrib.mako`` so that test
  collectors and similar tooling do not see spurious warnings;
* raise :class:`AttributeError` for unknown attributes.
"""

from __future__ import annotations

import importlib
import sys
import warnings


def test_bare_import_does_not_warn() -> None:
    sys.modules.pop("litestar.contrib.mako", None)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        importlib.import_module("litestar.contrib.mako")
    deprecation = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert deprecation == [], (
        "Bare `import litestar.contrib.mako` must not emit a DeprecationWarning, "
        f"got: {[str(w.message) for w in deprecation]}"
    )


def test_attribute_access_emits_deprecation_warning_for_engine() -> None:
    import litestar.contrib.mako as shim

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _ = shim.MakoTemplateEngine
    messages = [str(w.message) for w in caught if issubclass(w.category, DeprecationWarning)]
    assert messages, "Expected at least one DeprecationWarning"
    joined = " ".join(messages)
    assert "litestar.contrib.mako.MakoTemplateEngine" in joined
    assert "litestar.plugins.mako.MakoTemplateEngine" in joined


def test_attribute_access_emits_deprecation_warning_for_template() -> None:
    import litestar.contrib.mako as shim

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _ = shim.MakoTemplate
    messages = [str(w.message) for w in caught if issubclass(w.category, DeprecationWarning)]
    assert messages, "Expected at least one DeprecationWarning"
    joined = " ".join(messages)
    assert "litestar.contrib.mako.MakoTemplate" in joined
    assert "litestar.plugins.mako.MakoTemplate" in joined


def test_identity_equality_with_canonical_module() -> None:
    from litestar.contrib import mako as shim
    from litestar.plugins.mako import MakoTemplate, MakoTemplateEngine

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        assert shim.MakoTemplateEngine is MakoTemplateEngine
        assert shim.MakoTemplate is MakoTemplate


def test_unknown_attribute_raises_attribute_error() -> None:
    import litestar.contrib.mako as shim

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        try:
            _ = shim.NonexistentSymbol  # type: ignore[attr-defined]
        except AttributeError as exc:
            assert "NonexistentSymbol" in str(exc)
        else:
            raise AssertionError("Expected AttributeError on unknown attribute access")
