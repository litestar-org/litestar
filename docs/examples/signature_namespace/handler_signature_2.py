from __future__ import annotations

from typing import TYPE_CHECKING

from litestar import Controller, post

# Choose the appropriate noqa directive according to your linter
from domain import Model  # noqa: TCH002