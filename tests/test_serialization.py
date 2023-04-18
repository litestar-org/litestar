import json
from pathlib import Path
from typing import Any

import pydantic
import pytest
from pydantic import (
    BaseModel,
    ByteSize,
    ConstrainedBytes,
    ConstrainedDate,
    ConstrainedDecimal,
    ConstrainedFloat,
    ConstrainedFrozenSet,
    ConstrainedInt,
    ConstrainedList,
    ConstrainedSet,
    ConstrainedStr,
    EmailStr,
    NameEmail,
    PaymentCardNumber,
    SecretBytes,
    SecretStr,
)
from pydantic.color import Color

from litestar.exceptions import SerializationException
from litestar.serialization import (
    decode_json,
    decode_msgpack,
    default_serializer,
    encode_json,
    encode_msgpack,
)
from tests import PersonFactory

person = PersonFactory.build()


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
    path: Path = Path("example")

    email_str: pydantic.EmailStr = EmailStr("info@example.org")
    name_email: NameEmail = NameEmail("info", "info@example.org")
    color: Color = Color("rgb(255, 255, 255)")
    bytesize: ByteSize = ByteSize.validate("100b")
    secret_str: SecretStr = SecretStr("hello")
    secret_bytes: SecretBytes = SecretBytes(b"hello")
    payment_card_number: PaymentCardNumber = PaymentCardNumber("4000000000000002")

    constr: pydantic.constr() = ConstrainedStr("hello")  # type: ignore[valid-type]
    conbytes: pydantic.conbytes() = ConstrainedBytes(b"hello")  # type: ignore[valid-type]
    condate: pydantic.condate() = ConstrainedDate.today()  # type: ignore[valid-type]
    condecimal: pydantic.condecimal() = ConstrainedDecimal(3.14)  # type: ignore[valid-type]
    confloat: pydantic.confloat() = ConstrainedFloat(1.0)  # type: ignore[valid-type]
    conset: pydantic.conset(int) = ConstrainedSet([1])  # type: ignore[valid-type]
    confrozenset: pydantic.confrozenset(int) = ConstrainedFrozenSet([1])  # type: ignore[valid-type]
    conint: pydantic.conint() = ConstrainedInt(1)  # type: ignore[valid-type]
    conlist: pydantic.conlist(int, min_items=1) = ConstrainedList([1])  # type: ignore[valid-type]

    custom_str: CustomStr = CustomStr()
    custom_int: CustomInt = CustomInt()
    custom_float: CustomFloat = CustomFloat()
    custom_list: CustomList = CustomList()
    custom_set: CustomSet = CustomSet()
    custom_frozenset: CustomFrozenSet = CustomFrozenSet()
    custom_tuple: CustomTuple = CustomTuple()


model = Model()


@pytest.mark.parametrize(
    "value, expected",
    [
        (model.email_str, "info@example.org"),
        (model.name_email, "info <info@example.org>"),
        (model.color, "white"),
        (model.bytesize, 100),
        (model.secret_str, "**********"),
        (model.secret_bytes, "**********"),
        (model.payment_card_number, "4000000000000002"),
        (model.constr, "hello"),
        (model.conbytes, "hello"),
        (model.condate, model.condate.isoformat()),
        (model.condecimal, 3.14),
        (model.conset, {1}),
        (model.confrozenset, frozenset([1])),
        (model.conint, 1),
        (model, model.dict()),
        (model.custom_str, ""),
        (model.custom_int, 0),
        (model.custom_float, 0.0),
        (model.custom_set, set()),
        (model.custom_frozenset, frozenset()),
    ],
)
def test_default_serializer(value: Any, expected: Any) -> None:
    assert default_serializer(value) == expected


def test_pydantic_json_compatibility() -> None:
    assert json.loads(model.json()) == json.loads(encode_json(model))


@pytest.mark.parametrize("encoder", [encode_json, encode_msgpack])
def test_encoder_raises_serialization_exception(encoder: Any) -> None:
    with pytest.raises(SerializationException):
        encoder(object())


@pytest.mark.parametrize("decoder", [decode_json, decode_msgpack])
def test_decode_json_raises_serialization_exception(decoder: Any) -> None:
    with pytest.raises(SerializationException):
        decoder(b"str")


def test_decode_json_typed() -> None:
    model_json = model.json()
    assert decode_json(model_json, Model).json() == model_json


def test_decode_msgpack_typed() -> None:
    model_json = model.json()
    assert decode_msgpack(encode_msgpack(model), Model).json() == model_json
