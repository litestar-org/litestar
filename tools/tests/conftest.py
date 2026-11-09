import sys
from pathlib import Path

# the release scripts run as `python tools/<script>.py`, so they import their siblings as
# top-level modules; `tools/` has to be importable the same way for these tests to load them.
_TOOLS_DIR = str(Path(__file__).parents[1])
if _TOOLS_DIR not in sys.path:
    sys.path.append(_TOOLS_DIR)
