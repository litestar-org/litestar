def test_all_re_exports_are_importable() -> None:
    """Test that all items in __all__ can be imported from litestar.plugins.attrs."""
    from litestar.plugins.attrs import (
        AttrsSchemaPlugin as LitestarAttrsSchemaPlugin,
    )
    from litestar.plugins.attrs import (
        is_attrs_class as litestar_is_attrs_class,
    )

    # Verify all imports succeeded (no ImportError raised)
    assert LitestarAttrsSchemaPlugin is not None
    assert litestar_is_attrs_class is not None


def test_all_items_in_all_are_exported() -> None:
    """Test that all items listed in __all__ are actually exported."""
    from litestar.plugins import attrs

    expected_exports = {
        "AttrsSchemaPlugin",
        "is_attrs_class",
    }

    # Check that all items in __all__ are actually available as attributes
    for item_name in expected_exports:
        assert hasattr(attrs, item_name), f"{item_name} is missing from litestar.plugins.attrs"

    # Also verify that __all__ contains exactly what we expect
    assert set(attrs.__all__) == expected_exports
