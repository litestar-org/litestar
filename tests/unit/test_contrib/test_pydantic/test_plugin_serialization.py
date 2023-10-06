import datetime
import json
from decimal import Decimal
from functools import partial
from pathlib import Path
from typing import Any

import pydantic
import pytest
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

from litestar.contrib.pydantic import _model_dump, _model_dump_json
from litestar.contrib.pydantic.pydantic_init_plugin import PydanticInitPlugin

if VERSION.startswith("1"):
    from pydantic import (
        PaymentCardNumber,
    )
    from pydantic.color import Color
else:
    from pydantic_extra_types.color import Color  # type: ignore
    from pydantic_extra_types.payment import PaymentCardNumber  # type: ignore

from litestar.exceptions import SerializationException
from litestar.serialization import (
    decode_json,
    decode_msgpack,
    default_serializer,
    encode_json,
    encode_msgpack,
    get_serializer,
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
    condate: condate(ge=datetime.date.today())  # type: ignore
    condecimal: condecimal(ge=Decimal("1"))  # type: ignore
    confloat: confloat(ge=0)  # type: ignore

    conint: conint(ge=0)  # type: ignore


serializer = partial(default_serializer, type_encoders=PydanticInitPlugin.encoders())


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
        condate=datetime.date.today(),
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
        ("condate", datetime.date.today().isoformat()),
        ("condecimal", 3.14),
        ("conset", {1}),
        ("confrozenset", frozenset([1])),
        ("conint", 1),
    ],
)
def test_default_serializer(model: BaseModel, attribute_name: str, expected: Any) -> None:
    assert serializer(getattr(model, attribute_name)) == expected


def test_serialization_of_model_instance(model: BaseModel) -> None:
    assert serializer(getattr(model, "conbytes")) == b"hello"
    assert serializer(model) == _model_dump(model)


@pytest.mark.parametrize(
    "prefer_alias",
    [(False), (True)],
)
def test_pydantic_json_compatibility(model: BaseModel, prefer_alias: bool) -> None:
    raw = _model_dump_json(model, by_alias=prefer_alias)
    encoded_json = encode_json(model, serializer=get_serializer(PydanticInitPlugin.encoders(prefer_alias=prefer_alias)))

    raw_result = json.loads(raw)
    encoded_result = json.loads(encoded_json)

    if VERSION.startswith("1"):
        # pydantic v1 dumps decimals into floats as json, we therefore regard this as an error
        assert raw_result.get("condecimal") == float(encoded_result.get("condecimal"))
        del raw_result["condecimal"]
        del encoded_result["condecimal"]

    assert raw_result == encoded_result


@pytest.mark.parametrize("encoder", [encode_json, encode_msgpack])
def test_encoder_raises_serialization_exception(model: BaseModel, encoder: Any) -> None:
    with pytest.raises(SerializationException):
        encoder(object())


@pytest.mark.parametrize("decoder", [decode_json, decode_msgpack])
def test_decode_json_raises_serialization_exception(model: BaseModel, decoder: Any) -> None:
    with pytest.raises(SerializationException):
        decoder(b"str")


@pytest.mark.parametrize(
    "prefer_alias",
    [(False), (True)],
)
def test_decode_json_typed(model: BaseModel, prefer_alias: bool) -> None:
    dumped_model = _model_dump_json(model, by_alias=prefer_alias)
    decoded_model = decode_json(value=dumped_model, target_type=Model, type_decoders=PydanticInitPlugin.decoders())
    assert _model_dump_json(decoded_model, by_alias=prefer_alias) == dumped_model


@pytest.mark.parametrize(
    "prefer_alias",
    [(False), (True)],
)
def test_decode_msgpack_typed(model: BaseModel, prefer_alias: bool) -> None:
    model_json = _model_dump_json(model, by_alias=prefer_alias)
    assert (
        decode_msgpack(
            encode_msgpack(model, serializer=get_serializer(PydanticInitPlugin.encoders(prefer_alias=prefer_alias))),
            Model,
            type_decoders=PydanticInitPlugin.decoders(),
        ).json()
        == model_json
    )
