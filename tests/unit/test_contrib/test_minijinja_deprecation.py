"""Tests for the ``litestar.contrib.minijinja`` deprecation shim.

The shim must:

* re-export the public surface of :mod:`litestar.plugins.minijinja`
  (:class:`~litestar.plugins.minijinja.MiniJinjaTemplateEngine`,
  :class:`~litestar.plugins.minijinja.StateProtocol`,
  :class:`~litestar.plugins.minijinja.MiniJinjaTemplate`) plus the
  private ``_transform_state`` helper, while emitting a
  :class:`DeprecationWarning` on attribute access;
* preserve identity equality with the new module for every forwarded
  symbol;
* stay silent on bare ``import litestar.contrib.minijinja`` so that
  test collectors and similar tooling do not see spurious warnings;
* raise :class:`AttributeError` for unknown attributes.
"""

from __future__ import annotations

import importlib
import sys
import warnings


def test_bare_import_does_not_warn() -> None:
    sys.modules.pop("litestar.contrib.minijinja", None)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        importlib.import_module("litestar.contrib.minijinja")
    deprecation = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert deprecation == [], (
        "Bare `import litestar.contrib.minijinja` must not emit a "
        f"DeprecationWarning, got: {[str(w.message) for w in deprecation]}"
    )


def test_attribute_access_emits_deprecation_warning_for_engine() -> None:
    import litestar.contrib.minijinja as shim

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _ = shim.MiniJinjaTemplateEngine
    messages = [str(w.message) for w in caught if issubclass(w.category, DeprecationWarning)]
    assert messages, "Expected at least one DeprecationWarning"
    joined = " ".join(messages)
    assert "litestar.contrib.minijinja.MiniJinjaTemplateEngine" in joined
    assert "litestar.plugins.minijinja.MiniJinjaTemplateEngine" in joined


def test_attribute_access_emits_deprecation_warning_for_state_protocol() -> None:
    import litestar.contrib.minijinja as shim

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _ = shim.StateProtocol
    messages = [str(w.message) for w in caught if issubclass(w.category, DeprecationWarning)]
    assert any("StateProtocol" in m for m in messages)


def test_attribute_access_emits_deprecation_warning_for_private_transform_state() -> None:
    """The private ``_transform_state`` helper is still re-exported because
    historical consumers (notably ``litestar.plugins.flash``) imported it
    via the contrib path."""
    import litestar.contrib.minijinja as shim

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _ = shim._transform_state
    messages = [str(w.message) for w in caught if issubclass(w.category, DeprecationWarning)]
    assert any("_transform_state" in m for m in messages)


def test_identity_equality_with_canonical_module() -> None:
    from litestar.contrib import minijinja as shim
    from litestar.plugins.minijinja import (
        MiniJinjaTemplate,
        MiniJinjaTemplateEngine,
        StateProtocol,
        _transform_state,
    )

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        assert shim.MiniJinjaTemplateEngine is MiniJinjaTemplateEngine
        assert shim.StateProtocol is StateProtocol
        assert shim.MiniJinjaTemplate is MiniJinjaTemplate
        assert shim._transform_state is _transform_state


def test_unknown_attribute_raises_attribute_error() -> None:
    import litestar.contrib.minijinja as shim

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        try:
            _ = shim.NonexistentSymbol  # type: ignore[attr-defined]
        except AttributeError as exc:
            assert "NonexistentSymbol" in str(exc)
        else:
            raise AssertionError("Expected AttributeError on unknown attribute access")
