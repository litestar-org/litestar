"""Tests for the repository base class."""
from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from litestar.contrib.repository.exceptions import NotFoundError
from litestar.contrib.repository.testing.generic_mock_repository import (
    GenericMockRepository,
)

if TYPE_CHECKING:
    from pytest import MonkeyPatch


def test_repository_check_not_found_raises() -> None:
    """Test `check_not_found()` raises if `None`."""
    with pytest.raises(NotFoundError):
        GenericMockRepository.check_not_found(None)


def test_repository_check_not_found_returns_item() -> None:
    """Test `check_not_found()` returns the item if not `None`."""
    mock_item = MagicMock()
    assert GenericMockRepository.check_not_found(mock_item) is mock_item


def test_repository_get_id_attribute_value(monkeypatch: MonkeyPatch) -> None:
    """Test id attribute value retrieval."""
    monkeypatch.setattr(GenericMockRepository, "id_attribute", "random_attribute")
    mock = MagicMock()
    mock.random_attribute = "this one"
    assert GenericMockRepository.get_id_attribute_value(mock) == "this one"


def test_repository_set_id_attribute_value(monkeypatch: MonkeyPatch) -> None:
    """Test id attribute value setter."""
    monkeypatch.setattr(GenericMockRepository, "id_attribute", "random_attribute")
    mock = MagicMock()
    mock.random_attribute = "this one"
    mock = GenericMockRepository.set_id_attribute_value("no this one", mock)
    assert mock.random_attribute == "no this one"
