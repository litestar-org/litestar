from __future__ import annotations

from typing import TYPE_CHECKING, Generic, List, TypeVar
from unittest.mock import MagicMock

import pytest
from typing_extensions import Annotated, get_args, get_origin

from starlite.dto.exc import InvalidAnnotation
from starlite.dto.config import DTOConfig

from . import ExampleDTO, Model, SupportedT

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


def test_forward_referenced_type_argument_raises_exception() -> None:
    with pytest.raises(InvalidAnnotation):
        ExampleDTO["Model"]


def test_type_narrowing_with_scalar_type_arg() -> None:
    dto = ExampleDTO[Model]
    assert dto.config == DTOConfig()
    assert dto._postponed_cls_init_called is False
    assert dto.annotation is Model
    assert dto.model_type is Model


def test_type_narrowing_with_iterable_type_arg() -> None:
    dto = ExampleDTO[List[Model]]
    assert dto.config == DTOConfig()
    assert dto._postponed_cls_init_called is False
    assert get_origin(dto.annotation) is list
    assert get_args(dto.annotation) == (Model,)
    assert dto.model_type is Model


def test_type_narrowing_with_annotated_scalar_type_arg() -> None:
    config = DTOConfig()
    dto = ExampleDTO[Annotated[Model, config]]
    assert dto.config is config
    assert dto._postponed_cls_init_called is False
    assert dto.annotation is Model
    assert dto.model_type is Model


def test_type_narrowing_with_annotated_iterable_type_arg() -> None:
    config = DTOConfig()
    dto = ExampleDTO[Annotated[List[Model], config]]
    assert dto.config is config
    assert dto._postponed_cls_init_called is False
    assert get_origin(dto.annotation) is list
    assert get_args(dto.annotation) == (Model,)
    assert dto.model_type is Model


def test_type_narrowing_with_only_type_var() -> None:
    t = TypeVar("t", bound=Model)
    generic_dto = ExampleDTO[t]
    assert generic_dto is ExampleDTO


def test_type_narrowing_with_annotated_type_var() -> None:
    config = DTOConfig()
    t = TypeVar("t", bound=Model)
    generic_dto = ExampleDTO[Annotated[t, config]]
    assert generic_dto is not ExampleDTO
    assert issubclass(generic_dto, ExampleDTO)
    assert generic_dto.config is config
    assert not hasattr(generic_dto, "annotation")
    assert not hasattr(generic_dto, "model_type")


def test_unexpected_annotated_metadata_argument() -> None:
    with pytest.raises(InvalidAnnotation):
        ExampleDTO[Annotated[Model, object()]]


def test_extra_annotated_metadata_ignored() -> None:
    config = DTOConfig()
    dto = ExampleDTO[Annotated[Model, config]]
    assert dto.config is config


def test_config_provided_by_subclass() -> None:
    dto_config = DTOConfig()

    class DTOWithConfig(ExampleDTO[SupportedT], Generic[SupportedT]):
        config = dto_config

    dto = DTOWithConfig[Model]
    assert dto.config is dto_config


def test_overwrite_config() -> None:
    t = TypeVar("t", bound=Model)
    generic_dto = ExampleDTO[Annotated[t, DTOConfig()]]
    config = DTOConfig()
    dto = generic_dto[Annotated[Model, config]]  # pyright: ignore
    assert dto.config is config
