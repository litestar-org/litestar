from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from . import ExampleDTO, Model

if TYPE_CHECKING:
    from pytest import MonkeyPatch


def test_on_startup(monkeypatch: MonkeyPatch) -> None:
    dto_type = ExampleDTO[Model]
    postponed_cls_init_mock = MagicMock()
    monkeypatch.setattr(dto_type, "postponed_cls_init", postponed_cls_init_mock)
    # call startup twice
    dto_type.on_startup(Model)
    dto_type.on_startup(Model)
    assert postponed_cls_init_mock.called_once()
