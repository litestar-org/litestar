from dataclasses import dataclass
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from typing_extensions import TypedDict

from starlite.utils import model

if TYPE_CHECKING:
    from pytest import MonkeyPatch


def test_convert_dataclass_to_model_cache(monkeypatch: "MonkeyPatch") -> None:
    @dataclass
    class DC:
        a: str
        b: int

    response_mock = MagicMock()
    create_model_from_dataclass_mock = MagicMock(return_value=response_mock)
    monkeypatch.setattr(model, "create_model_from_dataclass", create_model_from_dataclass_mock)
    # test calling the function twice returns the expected response each time
    for _ in range(2):
        response = model.convert_dataclass_to_model(DC)
        assert response is response_mock
    # ensures that the work of the function has only been done once
    create_model_from_dataclass_mock.assert_called_once_with(DC)


def test_convert_typeddict_to_model_cache(monkeypatch: "MonkeyPatch") -> None:
    class TD(TypedDict):
        a: str
        b: int

    response_mock = MagicMock()
    create_model_from_typeddict_mock = MagicMock(return_value=response_mock)
    monkeypatch.setattr(model, "create_model_from_typeddict", create_model_from_typeddict_mock)
    # test calling the function twice returns the expected response each time
    for _ in range(2):
        response = model.convert_typeddict_to_model(TD)
        assert response is response_mock
    # ensures that the work of the function has only been done once
    create_model_from_typeddict_mock.assert_called_once_with(TD)
