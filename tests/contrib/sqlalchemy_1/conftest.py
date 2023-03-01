from __future__ import annotations

try:
    import sqlalchemy
except ImportError:
    collect_ignore_glob = ["*"]
else:
    if sqlalchemy.__version__.startswith("2."):
        collect_ignore_glob = ["*"]
