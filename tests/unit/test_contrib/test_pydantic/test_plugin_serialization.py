from __future__ import annotations

import datetime
import json
from decimal import Decimal
from functools import partial
from pathlib import Path
from typing import Any

import pydantic as pydantic_v2
import pytest
from pydantic import v1 as pydantic_v1
from pydantic.v1.color import Color as ColorV1
from pydantic_extra_types.color import Color as ColorV2

from litestar.contrib.pydantic import _model_dump, _model_dump_json
from litestar.contrib.pydantic.pydantic_init_plugin import PydanticInitPlugin
from litestar.exceptions import SerializationException
from litestar.serialization import (
    decode_json,
    decode_msgpack,
    default_serializer,
    encode_json,
    encode_msgpack,
    get_serializer,
)

from . import PydanticVersion


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


class ModelV1(pydantic_v1.BaseModel):
    class Config:
        arbitrary_types_allowed = True

    custom_str: CustomStr = CustomStr()
    custom_int: CustomInt = CustomInt()
    custom_float: CustomFloat = CustomFloat()
    custom_list: CustomList = CustomList()
    custom_set: CustomSet = CustomSet()
    custom_frozenset: CustomFrozenSet = CustomFrozenSet()
    custom_tuple: CustomTuple = CustomTuple()

    conset: pydantic_v1.conset(int, min_items=1)  # type: ignore[valid-type]
    confrozenset: pydantic_v1.confrozenset(int, min_items=1)  # type: ignore[valid-type]
    conlist: pydantic_v1.conlist(int, min_items=1)  # type: ignore[valid-type]

    path: Path

    email_str: pydantic_v1.EmailStr
    name_email: pydantic_v1.NameEmail
    color: ColorV1
    bytesize: pydantic_v1.ByteSize
    secret_str: pydantic_v1.SecretStr
    secret_bytes: pydantic_v1.SecretBytes
    payment_card_number: pydantic_v1.PaymentCardNumber

    constr: pydantic_v1.constr(min_length=1)  # type: ignore[valid-type]
    conbytes: pydantic_v1.conbytes(min_length=1)  # type: ignore[valid-type]
    condate: pydantic_v1.condate(ge=datetime.date.today())  # type: ignore[valid-type]
    condecimal: pydantic_v1.condecimal(ge=Decimal("1"))  # type: ignore[valid-type]
    confloat: pydantic_v1.confloat(ge=0)  # type: ignore[valid-type]

    conint: pydantic_v1.conint(ge=0)  # type: ignore[valid-type]

    url: pydantic_v1.AnyUrl
    http_url: pydantic_v1.HttpUrl


class ModelV2(pydantic_v2.BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    conset: pydantic_v2.conset(int, min_length=1)  # type: ignore[valid-type]
    confrozenset: pydantic_v2.confrozenset(int, min_length=1)  # type: ignore[valid-type]
    conlist: pydantic_v2.conlist(int, min_length=1)  # type: ignore[valid-type]

    path: Path

    email_str: pydantic_v2.EmailStr
    name_email: pydantic_v2.NameEmail
    color: ColorV2
    bytesize: pydantic_v2.ByteSize
    secret_str: pydantic_v2.SecretStr
    secret_bytes: pydantic_v2.SecretBytes
    payment_card_number: pydantic_v2.PaymentCardNumber

    constr: pydantic_v2.constr(min_length=1)  # type: ignore[valid-type]
    conbytes: pydantic_v2.conbytes(min_length=1)  # type: ignore[valid-type]
    condate: pydantic_v2.condate(ge=datetime.date.today())  # type: ignore[valid-type]
    condecimal: pydantic_v2.condecimal(ge=Decimal("1"))  # type: ignore[valid-type]
    confloat: pydantic_v2.confloat(ge=0)  # type: ignore[valid-type]

    conint: pydantic_v2.conint(ge=0)  # type: ignore[valid-type]

    url: pydantic_v2.AnyUrl
    http_url: pydantic_v2.HttpUrl


serializer = partial(default_serializer, type_encoders=PydanticInitPlugin.encoders())


@pytest.fixture()
def model_type(pydantic_version: PydanticVersion) -> type[ModelV1 | ModelV2]:
    return ModelV1 if pydantic_version == "v1" else ModelV2


@pytest.fixture()
def model(pydantic_version: PydanticVersion) -> ModelV1 | ModelV2:
    if pydantic_version == "v1":
        return ModelV1(
            path=Path("example"),
            email_str=pydantic_v1.parse_obj_as(pydantic_v1.EmailStr, "info@example.org"),
            name_email=pydantic_v1.NameEmail("info", "info@example.org"),
            color=ColorV1("rgb(255, 255, 255)"),
            bytesize=pydantic_v1.ByteSize(100),
            secret_str=pydantic_v1.SecretStr("hello"),
            secret_bytes=pydantic_v1.SecretBytes(b"hello"),
            payment_card_number=pydantic_v1.PaymentCardNumber("4000000000000002"),
            constr="hello",
            conbytes=b"hello",
            condate=datetime.date.today(),
            condecimal=Decimal("3.14"),
            confloat=1.0,
            conset={1},
            confrozenset=frozenset([1]),
            conint=1,
            conlist=[1],
            url="some://example.org/",  # type: ignore[arg-type]
            http_url="http://example.org/",  # type: ignore[arg-type]
        )
    return ModelV2(
        path=Path("example"),
        email_str=pydantic_v2.parse_obj_as(pydantic_v2.EmailStr, "info@example.org"),
        name_email=pydantic_v2.NameEmail("info", "info@example.org"),
        color=ColorV2("rgb(255, 255, 255)"),
        bytesize=pydantic_v2.ByteSize(100),
        secret_str=pydantic_v2.SecretStr("hello"),
        secret_bytes=pydantic_v2.SecretBytes(b"hello"),
        payment_card_number=pydantic_v2.PaymentCardNumber("4000000000000002"),
        constr="hello",
        conbytes=b"hello",
        condate=datetime.date.today(),
        condecimal=Decimal("3.14"),
        confloat=1.0,
        conset={1},
        confrozenset=frozenset([1]),
        conint=1,
        conlist=[1],
        url="some://example.org/",  # type: ignore[arg-type]
        http_url="http://example.org/",  # type: ignore[arg-type]
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
        ("url", "some://example.org/"),
        ("http_url", "http://example.org/"),
    ],
)
def test_default_serializer(model: ModelV1 | ModelV2, attribute_name: str, expected: Any) -> None:
    assert serializer(getattr(model, attribute_name)) == expected


def test_serialization_of_model_instance(model: ModelV1 | ModelV2) -> None:
    assert serializer(getattr(model, "conbytes")) == b"hello"
    assert serializer(model) == _model_dump(model)


@pytest.mark.parametrize("prefer_alias", [False, True])
def test_pydantic_json_compatibility(
    model: ModelV1 | ModelV2, prefer_alias: bool, pydantic_version: PydanticVersion
) -> None:
    raw = _model_dump_json(model, by_alias=prefer_alias)
    encoded_json = encode_json(model, serializer=get_serializer(PydanticInitPlugin.encoders(prefer_alias=prefer_alias)))

    raw_result = json.loads(raw)
    encoded_result = json.loads(encoded_json)

    if pydantic_version == "v1":
        # pydantic v1 dumps decimals into floats as json, we therefore regard this as an error
        assert raw_result.get("condecimal") == float(encoded_result.get("condecimal"))
        del raw_result["condecimal"]
        del encoded_result["condecimal"]

    assert raw_result == encoded_result


@pytest.mark.parametrize("encoder", [encode_json, encode_msgpack])
def test_encoder_raises_serialization_exception(model: ModelV1 | ModelV2, encoder: Any) -> None:
    with pytest.raises(SerializationException):
        encoder(object())


@pytest.mark.parametrize("decoder", [decode_json, decode_msgpack])
def test_decode_json_raises_serialization_exception(model: ModelV1 | ModelV2, decoder: Any) -> None:
    with pytest.raises(SerializationException):
        decoder(b"str")


@pytest.mark.parametrize("prefer_alias", [False, True])
def test_decode_json_typed(model: ModelV1 | ModelV2, prefer_alias: bool, model_type: type[ModelV1 | ModelV2]) -> None:
    dumped_model = _model_dump_json(model, by_alias=prefer_alias)
    decoded_model = decode_json(value=dumped_model, target_type=model_type, type_decoders=PydanticInitPlugin.decoders())
    assert _model_dump_json(decoded_model, by_alias=prefer_alias) == dumped_model  # type: ignore[arg-type]


@pytest.mark.parametrize("prefer_alias", [False, True])
def test_decode_msgpack_typed(
    model: ModelV1 | ModelV2, model_type: type[ModelV1 | ModelV2], prefer_alias: bool
) -> None:
    model_json = _model_dump_json(model, by_alias=prefer_alias)
    assert (
        decode_msgpack(
            encode_msgpack(model, serializer=get_serializer(PydanticInitPlugin.encoders(prefer_alias=prefer_alias))),
            model_type,
            type_decoders=PydanticInitPlugin.decoders(),
        ).json()  # type: ignore[attr-defined]
        == model_json
    )
