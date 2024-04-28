from __future__ import annotations

from starlite import get


@get("/")
def hello_world() -> dict[str, str]:
    return {"hello": "world"}
