"""Tests for the ``litestar.contrib.jinja`` deprecation shim.

The shim must:

* re-export :class:`~litestar.plugins.jinja.JinjaTemplateEngine` while
  emitting a :class:`DeprecationWarning` on attribute access;
* preserve identity equality with the new module;
* stay silent on bare ``import litestar.contrib.jinja`` so that test
  collectors and similar tooling do not see spurious warnings;
* raise :class:`AttributeError` for unknown attributes.
"""

from __future__ import annotations

import importlib
import sys
import warnings


def test_bare_import_does_not_warn() -> None:
    sys.modules.pop("litestar.contrib.jinja", None)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        importlib.import_module("litestar.contrib.jinja")
    deprecation = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert deprecation == [], (
        "Bare `import litestar.contrib.jinja` must not emit a DeprecationWarning, "
        f"got: {[str(w.message) for w in deprecation]}"
    )


def test_attribute_access_emits_deprecation_warning() -> None:
    import litestar.contrib.jinja as shim

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _ = shim.JinjaTemplateEngine
    messages = [str(w.message) for w in caught if issubclass(w.category, DeprecationWarning)]
    assert messages, "Expected at least one DeprecationWarning"
    joined = " ".join(messages)
    assert "litestar.contrib.jinja.JinjaTemplateEngine" in joined
    assert "litestar.plugins.jinja.JinjaTemplateEngine" in joined


def test_identity_equality_with_canonical_module() -> None:
    from litestar.contrib import jinja as shim
    from litestar.plugins.jinja import JinjaTemplateEngine

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        assert shim.JinjaTemplateEngine is JinjaTemplateEngine


def test_unknown_attribute_raises_attribute_error() -> None:
    import litestar.contrib.jinja as shim

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        try:
            _ = shim.NonexistentSymbol
        except AttributeError as exc:
            assert "NonexistentSymbol" in str(exc)
        else:
            raise AssertionError("Expected AttributeError on unknown attribute access")
