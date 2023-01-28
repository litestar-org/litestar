from enum import Enum

HTMX_STOP_POLLING = 286


class HX(str, Enum):
    """An Enum for HTMX Headers"""

    REDIRECT = "HX-Redirect"
    REFRESH = "HX-Refresh"
    PUSH_URL = "HX-Push-Url"
    RE_SWAP = "HX-Reswap"
    RE_TARGET = "HX-Retarget"
    LOCATION = "HX-Location"

    TRIGGER_EVENT = "HX-Trigger"
    TRIGGER_AFTER_SETTLE = "HX-Trigger-After-Settle"
    TRIGGER_AFTER_SWAP = "HX-Trigger-After-Swap"

    REQUEST = "HX-Request"
    BOOSTED = "HX-Boosted"
    CURRENT_URL = "HX-Current-URL"
    HISTORY_RESTORE_REQUEST = "HX-History-Restore-Request"
    PROMPT = "HX-Prompt"
    TARGET = "HX-Target"
    TRIGGER_ID = "HX-Trigger"
    TRIGGER_NAME = "HX-Trigger-Name"
    TRIGGERING_EVENT = "Triggering-Event"
