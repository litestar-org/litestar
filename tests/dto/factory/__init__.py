from __future__ import annotations

from dataclasses import dataclass


@dataclass(unsafe_hash=True)
class Model:
    a: int
    b: str
