from __future__ import annotations

import copy
import dataclasses
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Generic, TypeVar, Union

import pytest

from litestar import Litestar, Request, post
from litestar.dto import DataclassDTO, DTOConfig
from litestar.exceptions.dto_exceptions import InvalidAnnotationException
from litestar.params import JSONBody
from litestar.typing import FieldDefinition

from . import Model

if TYPE_CHECKING:
    from typing import Any

T = TypeVar("T", bound=Model)


def test_forward_referenced_type_argument_raises_exception() -> None:
    with pytest.raises(InvalidAnnotationException):
        DataclassDTO["Model"]


def test_union_type_argument_raises_exception() -> None:
    class ModelB(Model): ...

    with pytest.raises(InvalidAnnotationException):
        DataclassDTO[Union[Model, ModelB]]


def test_type_narrowing_with_scalar_type_arg() -> None:
    dto = DataclassDTO[Model]
    assert dto.config == DTOConfig()
    assert dto.model_type is Model  # type: ignore[misc]


def test_type_narrowing_with_annotated_scalar_type_arg() -> None:
    config = DTOConfig()
    dto = DataclassDTO[Annotated[Model, config]]
    assert dto.config is config
    assert dto.model_type is Model  # type: ignore[misc]


def test_type_narrowing_with_only_type_var() -> None:
    t = TypeVar("t", bound=Model)
    generic_dto = DataclassDTO[t]  # pyright: ignore[reportGeneralTypeIssues]
    assert generic_dto is DataclassDTO


def test_type_narrowing_with_annotated_type_var() -> None:
    config = DTOConfig()
    t = TypeVar("t", bound=Model)
    generic_dto = DataclassDTO[Annotated[t, config]]  # pyright: ignore[reportGeneralTypeIssues]
    assert generic_dto is not DataclassDTO
    assert issubclass(generic_dto, DataclassDTO)
    assert generic_dto.config is config
    assert not hasattr(generic_dto, "model_type")


def test_extra_annotated_metadata_ignored() -> None:
    config = DTOConfig()
    dto = DataclassDTO[Annotated[Model, config, "a"]]
    assert dto.config is config


def test_overwrite_config() -> None:
    first = DTOConfig(exclude={"a"})
    generic_dto = DataclassDTO[Annotated[T, first]]  # pyright: ignore[reportGeneralTypeIssues]
    second = DTOConfig(exclude={"b"})
    dto = generic_dto[Annotated[Model, second]]  # pyright: ignore[reportInvalidTypeArguments]
    assert dto.config is second


def test_existing_config_not_overwritten() -> None:
    assert getattr(DataclassDTO, "_config", None) is None
    first = DTOConfig(exclude={"a"})
    generic_dto = DataclassDTO[Annotated[T, first]]  # pyright: ignore[reportGeneralTypeIssues]
    dto = generic_dto[Model]  # pyright: ignore[reportInvalidTypeArguments]
    assert dto.config is first


def test_config_assigned_via_subclassing() -> None:
    class CustomGenericDTO(DataclassDTO[T]):
        config = DTOConfig(exclude={"a"})

    concrete_dto = CustomGenericDTO[Model]

    assert concrete_dto.config.exclude == {"a"}


async def test_from_bytes(asgi_connection: Request[Any, Any, Any]) -> None:
    dto_type = DataclassDTO[Model]
    asgi_connection.route_handler.data_backend = dto_type.create_for_field_definition(
        FieldDefinition.from_annotation(JSONBody[Model]), handler_id=asgi_connection.route_handler.handler_id
    )
    assert dto_type(asgi_connection).decode_bytes(b'{"a":1,"b":"two"}') == Model(a=1, b="two")


def test_config_field_rename(asgi_connection: Request[Any, Any, Any]) -> None:
    config = DTOConfig(rename_fields={"a": "z"})
    dto_type = DataclassDTO[Annotated[Model, config]]
    backend = dto_type.create_for_field_definition(
        FieldDefinition.from_annotation(JSONBody[Model]), handler_id="handler_id"
    )
    field_definitions = backend.parsed_field_definitions
    assert field_definitions[0].serialization_name == "z"


def test_type_narrowing_with_multiple_configs() -> None:
    config_1 = DTOConfig()
    config_2 = DTOConfig()
    dto = DataclassDTO[Annotated[Model, config_1, config_2]]
    assert dto.config is config_1


def test_raises_invalid_annotation_for_non_homogenous_collection_types() -> None:
    dto_type = DataclassDTO[Model]

    with pytest.raises(InvalidAnnotationException):
        dto_type.create_for_field_definition(
            handler_id="handler",
            field_definition=FieldDefinition.from_annotation(tuple[Model, str]),
        )


def test_raises_invalid_annotation_for_mismatched_types() -> None:
    dto_type = DataclassDTO[Model]

    @dataclass
    class OtherModel:
        a: int

    with pytest.raises(InvalidAnnotationException):
        dto_type.create_for_field_definition(
            handler_id="handler", field_definition=FieldDefinition.from_annotation(OtherModel)
        )


def test_sub_types_supported() -> None:
    dto_type = DataclassDTO[Model]

    @dataclass
    class SubType(Model):
        c: int

    backend = dto_type.create_for_field_definition(
        handler_id="handler_id", field_definition=FieldDefinition.from_annotation(JSONBody[SubType])
    )
    assert backend.parsed_field_definitions[-1].name == "c"


def test_dto_class_holds_no_handler_state() -> None:
    dto_type = DataclassDTO[Model]

    def class_state() -> dict[tuple[type, str], Any]:
        return {
            (cls, name): copy.copy(value)
            for cls in dto_type.__mro__
            for name, value in vars(cls).items()
            if isinstance(value, (dict, list, set))
        }

    state_before = class_state()

    @post("/one", dto=dto_type, name="one")
    def one(data: JSONBody[Model]) -> Model:
        return data

    @post("/two", dto=dto_type, name="two")
    def two(data: JSONBody[Model]) -> Model:
        return data

    handlers = [
        app.get_handler_index_by_name(name)["handler"]  # type: ignore[index]
        for app in (Litestar([one, two]), Litestar([one]))
        for name in ("one", "two")
        if app.get_handler_index_by_name(name)
    ]
    backends = [backend for handler in handlers for backend in (handler.data_backend, handler.return_backend)]

    assert len(handlers) == 3
    assert all(backend is not None for backend in backends)
    assert len({id(backend) for backend in backends}) == 6
    assert class_state() == state_before


def test_get_config_for_model_type() -> None:
    base_config = DTOConfig(rename_strategy="camel")

    class CustomDTO(DataclassDTO[T], Generic[T]):
        @classmethod
        def get_config_for_model_type(cls, config: DTOConfig, model_type: type[Any]) -> DTOConfig:
            return dataclasses.replace(config, exclude={"foo"})

    annotated_dto = CustomDTO[Model]
    annotated_dto_with_config = CustomDTO[Annotated[Model, base_config]]

    class SubclassDTO(CustomDTO[Model]):
        pass

    class SubclassDTOWithConfig(CustomDTO[Model]):
        config = base_config

    assert annotated_dto.config.exclude == {"foo"}
    assert SubclassDTO.config.exclude == {"foo"}

    # we expect existing configs to have been merged
    assert annotated_dto_with_config.config.exclude == {"foo"}
    assert annotated_dto_with_config.config.rename_strategy == "camel"

    assert SubclassDTOWithConfig.config.exclude == {"foo"}
    assert SubclassDTOWithConfig.config.rename_strategy == "camel"
