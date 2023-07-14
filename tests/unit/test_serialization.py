import json
from pathlib import Path
from typing import Any

import pydantic
import pytest
from _decimal import Decimal
from dateutil.utils import today
from pydantic import (
    VERSION,
    BaseModel,
    ByteSize,
    EmailStr,
    NameEmail,
    SecretBytes,
    SecretStr,
    conbytes,
    condate,
    condecimal,
    confloat,
    confrozenset,
    conint,
    conlist,
    conset,
    constr,
)

if VERSION.startswith("1"):
    from pydantic import (
        PaymentCardNumber,
    )
    from pydantic.color import Color
else:
    from pydantic_extra_types.color import Color  # type: ignore
    from pydantic_extra_types.payment import PaymentCardNumber  # type: ignore

from litestar.enums import MediaType
from litestar.exceptions import SerializationException
from litestar.serialization import (
    decode_json,
    decode_media_type,
    decode_msgpack,
    default_serializer,
    encode_json,
    encode_msgpack,
)


class CustomStr(str):
    pass


class CustomInt(int):
    pass


class CustomFloat(float):
    pass


class CustomList(list):
    pass


class CustomSet(set):
    pass


class CustomFrozenSet(frozenset):
    pass


class CustomTuple(tuple):
    pass


class Model(BaseModel):
    if VERSION.startswith("1"):

        class Config:
            arbitrary_types_allowed = True

        custom_str: CustomStr = CustomStr()
        custom_int: CustomInt = CustomInt()
        custom_float: CustomFloat = CustomFloat()
        custom_list: CustomList = CustomList()
        custom_set: CustomSet = CustomSet()
        custom_frozenset: CustomFrozenSet = CustomFrozenSet()
        custom_tuple: CustomTuple = CustomTuple()

        conset: conset(int, min_items=1)  # type: ignore
        confrozenset: confrozenset(int, min_items=1)  # type: ignore
        conlist: conlist(int, min_items=1) if pydantic.VERSION.startswith("2") else conlist(int, min_items=1)  # type: ignore

    else:
        model_config = {"arbitrary_types_allowed": True}
        conset: conset(int, min_length=1)  # type: ignore
        confrozenset: confrozenset(int, min_length=1)  # type: ignore
        conlist: conlist(int, min_length=1) if pydantic.VERSION.startswith("2") else conlist(int, min_items=1)  # type: ignore

    path: Path

    email_str: EmailStr
    name_email: NameEmail
    color: Color
    bytesize: ByteSize
    secret_str: SecretStr
    secret_bytes: SecretBytes
    payment_card_number: PaymentCardNumber

    constr: constr(min_length=1)  # type: ignore
    conbytes: conbytes(min_length=1)  # type: ignore
    condate: condate(ge=today().date())  # type: ignore
    condecimal: condecimal(ge=Decimal("1"))  # type: ignore
    confloat: confloat(ge=0)  # type: ignore

    conint: conint(ge=0)  # type: ignore


@pytest.fixture()
def model() -> Model:
    return Model(
        path=Path("example"),
        email_str="info@example.org",
        name_email=NameEmail("info", "info@example.org"),
        color=Color("rgb(255, 255, 255)"),
        bytesize=ByteSize(100),
        secret_str=SecretStr("hello"),
        secret_bytes=SecretBytes(b"hello"),
        payment_card_number=PaymentCardNumber("4000000000000002"),
        constr="hello",
        conbytes=b"hello",
        condate=today(),
        condecimal=Decimal("3.14"),
        confloat=1.0,
        conset={1},
        confrozenset=frozenset([1]),
        conint=1,
        conlist=[1],
    )


@pytest.mark.parametrize(
    "attribute_name, expected",
    [
        ("path", "example"),
        ("email_str", "info@example.org"),
        ("name_email", "info <info@example.org>"),
        ("color", "white"),
        ("bytesize", 100),
        ("secret_str", "**********"),
        ("secret_bytes", "**********"),
        ("payment_card_number", "4000000000000002"),
        ("constr", "hello"),
        ("conbytes", b"hello"),
        ("condate", today().date().isoformat()),
        ("condecimal", 3.14),
        ("conset", {1}),
        ("confrozenset", frozenset([1])),
        ("conint", 1),
    ],
)
def test_default_serializer(model: BaseModel, attribute_name: str, expected: Any) -> None:
    assert default_serializer(getattr(model, attribute_name)) == expected


def test_serialization_of_model_instance(model: BaseModel) -> None:
    assert default_serializer(model) == model.model_dump(mode="json") if hasattr(model, "model_dump") else model.dict()


def test_pydantic_json_compatibility(model: BaseModel) -> None:
    raw = model.model_dump_json() if hasattr(model, "model_dump_json") else model.json()
    encoded_json = encode_json(model)
    assert json.loads(raw) == json.loads(encoded_json)


@pytest.mark.parametrize("encoder", [encode_json, encode_msgpack])
def test_encoder_raises_serialization_exception(model: BaseModel, encoder: Any) -> None:
    with pytest.raises(SerializationException):
        encoder(object())


@pytest.mark.parametrize("decoder", [decode_json, decode_msgpack])
def test_decode_json_raises_serialization_exception(model: BaseModel, decoder: Any) -> None:
    with pytest.raises(SerializationException):
        decoder(b"str")


def test_decode_json_typed(model: BaseModel) -> None:
    dumped_model = model.model_dump_json() if hasattr(model, "model_dump_json") else model.json()
    decoded_model = decode_json(dumped_model, Model)
    assert (
        decoded_model.model_dump_json() if hasattr(decoded_model, "model_dump_json") else decoded_model.json()
    ) == dumped_model


def test_decode_msgpack_typed(model: BaseModel) -> None:
    model_json = model.json()
    assert decode_msgpack(encode_msgpack(model), Model).json() == model_json


def test_decode_media_type(model: BaseModel) -> None:
    model_json = model.json()
    assert decode_media_type(model_json.encode("utf-8"), MediaType.JSON, Model).json() == model_json
    assert decode_media_type(encode_msgpack(model), MediaType.MESSAGEPACK, Model).json() == model_json


def test_decode_media_type_unsupported_media_type(model: BaseModel) -> None:
    with pytest.raises(SerializationException):
        decode_media_type(b"", MediaType.HTML, Model)
