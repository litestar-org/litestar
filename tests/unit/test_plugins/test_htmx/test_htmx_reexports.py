"""Test that all htmx re-exports from litestar.plugins.htmx are working correctly."""


def test_all_re_exports_are_importable() -> None:
    """Test that all items in __all__ can be imported from litestar.plugins.htmx."""
    from litestar.plugins.htmx import (
        ClientRedirect as LitestarClientRedirect,
    )
    from litestar.plugins.htmx import (
        ClientRefresh as LitestarClientRefresh,
    )
    from litestar.plugins.htmx import (
        EventAfterType as LitestarEventAfterType,
    )
    from litestar.plugins.htmx import (
        HTMXConfig as LitestarHTMXConfig,
    )
    from litestar.plugins.htmx import (
        HTMXDetails as LitestarHTMXDetails,
    )
    from litestar.plugins.htmx import (
        HTMXHeaders as LitestarHTMXHeaders,
    )
    from litestar.plugins.htmx import (
        HtmxHeaderType as LitestarHtmxHeaderType,
    )
    from litestar.plugins.htmx import (
        HTMXPlugin as LitestarHTMXPlugin,
    )
    from litestar.plugins.htmx import (
        HTMXRequest as LitestarHTMXRequest,
    )
    from litestar.plugins.htmx import (
        HTMXTemplate as LitestarHTMXTemplate,
    )
    from litestar.plugins.htmx import (
        HXLocation as LitestarHXLocation,
    )
    from litestar.plugins.htmx import (
        HXStopPolling as LitestarHXStopPolling,
    )
    from litestar.plugins.htmx import (
        LocationType as LitestarLocationType,
    )
    from litestar.plugins.htmx import (
        PushUrl as LitestarPushUrl,
    )
    from litestar.plugins.htmx import (
        PushUrlType as LitestarPushUrlType,
    )
    from litestar.plugins.htmx import (
        ReplaceUrl as LitestarReplaceUrl,
    )
    from litestar.plugins.htmx import (
        Reswap as LitestarReswap,
    )
    from litestar.plugins.htmx import (
        ReSwapMethod as LitestarReSwapMethod,
    )
    from litestar.plugins.htmx import (
        Retarget as LitestarRetarget,
    )
    from litestar.plugins.htmx import (
        TriggerEvent as LitestarTriggerEvent,
    )
    from litestar.plugins.htmx import (
        TriggerEventType as LitestarTriggerEventType,
    )
    from litestar.plugins.htmx import (
        _utils as litestar_utils,
    )

    # Verify all imports succeeded (no ImportError raised)
    assert LitestarClientRedirect is not None
    assert LitestarClientRefresh is not None
    assert LitestarEventAfterType is not None
    assert LitestarHTMXConfig is not None
    assert LitestarHTMXDetails is not None
    assert LitestarHTMXHeaders is not None
    assert LitestarHTMXPlugin is not None
    assert LitestarHTMXRequest is not None
    assert LitestarHTMXTemplate is not None
    assert LitestarHXLocation is not None
    assert LitestarHXStopPolling is not None
    assert LitestarHtmxHeaderType is not None
    assert LitestarLocationType is not None
    assert LitestarPushUrl is not None
    assert LitestarPushUrlType is not None
    assert LitestarReplaceUrl is not None
    assert LitestarReswap is not None
    assert LitestarReSwapMethod is not None
    assert LitestarRetarget is not None
    assert LitestarTriggerEvent is not None
    assert LitestarTriggerEventType is not None
    assert litestar_utils is not None


def test_all_items_in_all_are_exported() -> None:
    """Test that all items listed in __all__ are actually exported."""
    from litestar.plugins import htmx

    expected_exports = {
        "ClientRedirect",
        "ClientRefresh",
        "EventAfterType",
        "HTMXConfig",
        "HTMXDetails",
        "HTMXHeaders",
        "HTMXPlugin",
        "HTMXRequest",
        "HTMXTemplate",
        "HXLocation",
        "HXStopPolling",
        "HtmxHeaderType",
        "LocationType",
        "PushUrl",
        "PushUrlType",
        "ReSwapMethod",
        "ReplaceUrl",
        "Reswap",
        "Retarget",
        "TriggerEvent",
        "TriggerEventType",
        "_utils",
    }

    # Check that all items in __all__ are actually available as attributes
    for item_name in expected_exports:
        assert hasattr(htmx, item_name), f"{item_name} is missing from litestar.plugins.htmx"

    # Also verify that __all__ contains exactly what we expect
    assert set(htmx.__all__) == expected_exports
