import importlib.util
import sys
from pathlib import Path
from typing import Union


def purge_module(module_names: list[str], path: Union[str, Path]) -> None:
    for name in module_names:
        if name in sys.modules:
            del sys.modules[name]
    Path(importlib.util.cache_from_source(path)).unlink(missing_ok=True)
