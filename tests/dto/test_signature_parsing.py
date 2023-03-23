from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from starlite._signature.parsing import create_signature_model
from starlite.dto.stdlib.dataclass import DataclassDTO

from . import Model

if TYPE_CHECKING:
    from pytest import MonkeyPatch


def test_create_signature_model(monkeypatch: MonkeyPatch) -> None:
    data_dto = DataclassDTO[Model]
    ret_dto = DataclassDTO[Model]
    mocks = []
    for dto in data_dto, ret_dto:
        mock = MagicMock()
        monkeypatch.setattr(dto, "on_startup", mock)
        mocks.append(mock)

    def func(data: data_dto) -> ret_dto:
        return data

    signature_model = create_signature_model(
        func, plugins=[], dependency_name_set=set(), signature_namespace={"data_dto": data_dto, "ret_dto": ret_dto}
    )
    assert signature_model.fields["data"].has_dto_annotation
    assert signature_model.return_annotation is ret_dto
    for mock, dto in zip(mocks, [data_dto, ret_dto]):
        mock.assert_called_once_with(dto)
