from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from starlite._kwargs.kwargs_model import KwargsModel
from starlite._signature.utils import create_signature_model
from starlite.dto.factory.stdlib.dataclass import DataclassDTO
from starlite.types.parsed_signature import ParsedSignature

from . import Model

if TYPE_CHECKING:
    from pytest import MonkeyPatch

    from starlite._signature.models import SignatureModel


@pytest.fixture
def parsed_signature() -> ParsedSignature:
    def func(data: DataclassDTO[Model]) -> None:
        ...

    return ParsedSignature.from_fn(func, {"Model": Model})


@pytest.fixture
def signature_model(monkeypatch: MonkeyPatch, parsed_signature: ParsedSignature) -> type[SignatureModel]:
    def func(data: DataclassDTO[Model]) -> None:
        ...

    return create_signature_model(set(), func, [], "attrs", parsed_signature)


def test_kwargs_model(signature_model: type[SignatureModel], parsed_signature: ParsedSignature) -> None:
    kwargs_model = KwargsModel.create_for_signature_model(
        signature_model=signature_model,
        dependencies={},
        path_parameters=set(),
        layered_parameters={},
        data_dto=None,
        parsed_signature=parsed_signature,
    )
    assert kwargs_model.expected_dto_data
