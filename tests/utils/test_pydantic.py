from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from typing_extensions import TypedDict

from litestar.utils.pydantic import (
    convert_dataclass_to_model,
    convert_typeddict_to_model,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_convert_dataclass_to_model_cache(mocker: MockerFixture) -> None:
    @dataclass
    class DC:
        a: str
        b: int

    response_mock = MagicMock()
    create_model_from_dataclass_mock = mocker.patch(
        "litestar.utils.pydantic.create_model_from_dataclass", return_value=response_mock
    )
    # test calling the function twice returns the expected response each time
    for _ in range(2):
        response = convert_dataclass_to_model(DC)
        assert response is response_mock
    # ensures that the work of the function has only been done once
    create_model_from_dataclass_mock.assert_called_once_with(DC)


def test_convert_typeddict_to_model_cache(mocker: MockerFixture) -> None:
    class TD(TypedDict):
        a: str
        b: int

    response_mock = MagicMock()
    create_model_from_typeddict_mock = mocker.patch(
        "litestar.utils.pydantic.create_model_from_typeddict", return_value=response_mock
    )
    # test calling the function twice returns the expected response each time
    for _ in range(2):
        response = convert_typeddict_to_model(TD)
        assert response is response_mock
    # ensures that the work of the function has only been done once
    create_model_from_typeddict_mock.assert_called_once_with(TD)
