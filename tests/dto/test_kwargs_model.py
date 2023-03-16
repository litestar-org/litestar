from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from starlite._kwargs.kwargs_model import KwargsModel
from starlite._signature.parsing import create_signature_model
from starlite.dto.stdlib.dataclass import DataclassDTO

from . import Model

if TYPE_CHECKING:
    from pytest import MonkeyPatch

    from starlite._signature.models import SignatureModel


@pytest.fixture
def signature_model(monkeypatch: MonkeyPatch) -> type[SignatureModel]:
    def func(data: DataclassDTO[Model]) -> None:
        ...

    return create_signature_model(func, [], set(), namespace={"ExampleDTO": DataclassDTO, "Model": Model})


def test_kwargs_model(signature_model: type[SignatureModel]) -> None:
    kwargs_model = KwargsModel.create_for_signature_model(
        signature_model=signature_model, dependencies={}, path_parameters=set(), layered_parameters={}
    )
    assert kwargs_model.expected_dto_data
