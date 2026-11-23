# pyright: reportUnnecessaryTypeIgnoreComment=false

from __future__ import annotations

import warnings
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated, Any, Literal, Optional, Union, cast

import msgspec
import pydantic as pydantic_v2
import pytest
from msgspec import UnsetType
from pydantic import AwareDatetime

from litestar import Litestar, Request, post
from litestar.dto import DTOConfig, MsgspecDTO
from litestar.dto._backend import DTOBackend
from litestar.exceptions import LitestarDeprecationWarning
from litestar.params import JSONBody, KwargDefinition
from litestar.plugins.pydantic import PydanticDTO, _model_dump, _model_dump_json
from litestar.status_codes import HTTP_201_CREATED
from litestar.testing import create_test_client
from litestar.typing import FieldDefinition

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType

    from pydantic import BaseModel


def test_aware_datetime_serialization_v2() -> None:
    class PydanticAwareDatetimeModel(pydantic_v2.BaseModel):
        tz_aware_datetime: AwareDatetime

    class AwareDatetimeDTO(PydanticDTO[PydanticAwareDatetimeModel]):
        pass

    @post(dto=AwareDatetimeDTO, signature_types=[PydanticAwareDatetimeModel])
    def handler(data: JSONBody[PydanticAwareDatetimeModel]) -> PydanticAwareDatetimeModel:
        return data

    with create_test_client(handler) as client:
        data = PydanticAwareDatetimeModel(tz_aware_datetime=datetime.now(tz=UTC))
        dict_payload = _model_dump(data)
        json_payload = _model_dump_json(data)

        headers = {"Content-Type": "application/json; charset=utf-8"}
        response = client.post(
            "/",
            content=json_payload,
            headers=headers,
        )
        assert response.status_code == HTTP_201_CREATED
        assert response.json() == dict_payload


def test_schema_required_fields_with_pydantic_dto(base_model: type[BaseModel]) -> None:
    class PydanticUser(base_model):  # type: ignore[misc, valid-type]
        age: int
        name: str

    class UserDTO(PydanticDTO[PydanticUser]):
        pass

    @post(dto=UserDTO, return_dto=None, signature_types=[PydanticUser])
    def handler(data: JSONBody[PydanticUser], request: Request) -> dict:
        schema = request.app.openapi_schema
        return schema.to_schema()

    with create_test_client(handler) as client:
        data = PydanticUser(name="A", age=10)
        headers = {"Content-Type": "application/json; charset=utf-8"}
        received = client.post(
            "/",
            content=_model_dump_json(data),
            headers=headers,
        )
        required = next(iter(received.json()["components"]["schemas"].values()))["required"]
        assert len(required) == 2


def test_field_definition_implicit_optional_default(base_model: type[BaseModel]) -> None:
    class Model(base_model):  # type: ignore[misc, valid-type]
        a: Optional[str]

    dto_type = PydanticDTO[Model]
    field_defs = list(dto_type.generate_field_definitions(Model))
    assert len(field_defs) == 1
    assert field_defs[0].default is None


def test_pydantic_field_descriptions(create_module: Callable[[str], ModuleType]) -> None:
    module = create_module(
        """
from litestar import Litestar, get
from litestar.plugins.pydantic import PydanticDTO
from litestar.dto import DTOConfig
from pydantic import BaseModel, Field
from typing_extensions import Annotated

class User(BaseModel):
    id: Annotated[
        int,
        Field(description="This is a test (id description).", gt=1),
    ]

class DataCollectionDTO(PydanticDTO[User]):
    config = DTOConfig(rename_strategy="camel")

@get("/user", return_dto=DataCollectionDTO, sync_to_thread=False)
def get_user() -> User:
    return User(id=user_id)

app = Litestar(route_handlers=[get_user])
        """
    )
    app = cast(Litestar, module.app)
    schema = app.openapi_schema
    assert schema.components.schemas is not None
    component_schema = schema.components.schemas["GetUserUserResponseBody"]
    assert component_schema.properties is not None
    assert component_schema.properties["id"].description == "This is a test (id description)."
    assert component_schema.properties["id"].exclusive_minimum == 1  # type: ignore[union-attr]


@pytest.mark.parametrize(
    "model_config_option, forbid_unknown_fields_default, expected_dto_config_option",
    [
        ("forbid", False, True),
        ("forbid", True, True),
        ("allow", False, False),
        ("allow", True, True),
        ("ignore", True, True),
        ("ignore", False, False),
    ],
)
def test_forbid_unknown_fields_if_forbid_extra_is_set_v2(
    forbid_unknown_fields_default: bool,
    model_config_option: Literal["forbid", "allow", "ignore"],
    expected_dto_config_option: bool,
) -> None:
    class Model(pydantic_v2.BaseModel):
        a: str
        model_config = pydantic_v2.ConfigDict(extra=model_config_option)

    dto_config = DTOConfig(
        max_nested_depth=2,
        # config set on the pydantic model should take precedence
        forbid_unknown_fields=forbid_unknown_fields_default,
    )
    dto = PydanticDTO[Annotated[Model, dto_config]]

    assert dto.config.forbid_unknown_fields is expected_dto_config_option
    # ensure the config is merged
    assert dto.config.max_nested_depth == 2


@pytest.mark.parametrize("excluded_name", ["user's note", "other'] = 2 #"])
def test_excluded_field_name_not_valid_as_string_literal(excluded_name: str) -> None:
    model = pydantic_v2.create_model("QuotedFieldName", **{"other": (int, 0), excluded_name: (int, 0)})  # type: ignore[call-overload]
    dto_config = DTOConfig(exclude={excluded_name})

    @post(
        dto=PydanticDTO[Annotated[model, dto_config]], return_dto=None, signature_namespace={"QuotedFieldName": model}
    )
    def handler(data: JSONBody[QuotedFieldName]) -> dict[str, int]:  # type: ignore[name-defined]  # noqa: F821
        return data.model_dump()  # type: ignore[no-any-return]

    with create_test_client(handler) as client:
        response = client.post("/", json={"other": 1})

    assert response.status_code == HTTP_201_CREATED
    assert response.json() == {"other": 1, excluded_name: 0}


def test_experimental_codegen_backend_warns_once_with_forbid_extra() -> None:
    class Model(pydantic_v2.BaseModel):
        a: str
        model_config = pydantic_v2.ConfigDict(extra="forbid")

    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        dto = PydanticDTO[Annotated[Model, DTOConfig(experimental_codegen_backend=False)]]

    assert [w.category for w in record] == [LitestarDeprecationWarning]
    assert dto.config.forbid_unknown_fields is True


class PInner(pydantic_v2.BaseModel):
    a: int
    b: str = "b"


class POuter(pydantic_v2.BaseModel):
    pair: tuple[PInner, int]


def test_pydantic_dto_fixed_length_tuple_of_models() -> None:
    @post(dto=PydanticDTO[Annotated[POuter, DTOConfig(exclude={"pair.0.b"})]])
    def handler(data: JSONBody[POuter]) -> POuter:
        return data

    with create_test_client(handler) as client:
        response = client.post("/", json={"pair": [{"a": 1}, 2]})

    assert response.status_code == HTTP_201_CREATED
    assert response.json() == {"pair": [{"a": 1}, 2]}


@pytest.mark.parametrize(
    "partial, expected",
    [
        (False, Annotated[int, KwargDefinition(ge=1)]),
        (True, Annotated[Union[int, UnsetType], KwargDefinition(ge=1)]),
    ],
)
def test_transfer_model_field_annotations(partial: bool, expected: Any) -> None:
    field_type: Any = Annotated[int, pydantic_v2.Field(ge=1)]
    model = pydantic_v2.create_model("Model", f=(field_type, 1))
    dto = type("ModelDTO", (PydanticDTO[model],), {"config": DTOConfig(partial=partial)})
    backend = DTOBackend(
        handler_id="test",
        dto_factory=dto,
        field_definition=FieldDefinition.from_annotation(model),
        model_type=model,
        wrapper_attribute_name=None,
        is_data_field=True,
    )
    assert backend.transfer_model_type.__annotations__["f"] == expected


def test_msgspec_dto_does_not_enforce_pydantic_decimal_constraint() -> None:
    struct = msgspec.defstruct("Model", [("f", pydantic_v2.condecimal(gt=0))])

    @post("/", dto=MsgspecDTO[struct], return_dto=None, signature_namespace={"struct": struct})  # type: ignore[valid-type]
    def create_condecimal(data: JSONBody[struct]) -> None:  # type: ignore[valid-type]
        pass

    with create_test_client(create_condecimal, openapi_config=None) as client:
        assert client.post("/", json={"f": "0"}).status_code == HTTP_201_CREATED
        assert client.post("/", json={"f": "1"}).status_code == HTTP_201_CREATED


class PUnionMember1(pydantic_v2.BaseModel):
    a: int


class PUnionMember2(pydantic_v2.BaseModel):
    b: int


class PUnionHolder(pydantic_v2.BaseModel):
    f: Union[PUnionMember1, PUnionMember2]


def test_pydantic_dto_over_union_of_models_is_not_checked_at_startup() -> None:
    @post("/", dto=PydanticDTO[PUnionHolder], return_dto=None)
    def create_pydantic_union_holder(data: JSONBody[PUnionHolder]) -> None:
        pass

    Litestar(route_handlers=[create_pydantic_union_holder], openapi_config=None)
