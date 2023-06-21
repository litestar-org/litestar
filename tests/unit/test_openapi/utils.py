from datetime import date, timedelta
from decimal import Decimal
from enum import Enum

import pydantic
from pydantic import (
    conbytes,
    condate,
    condecimal,
    confloat,
    conint,
    conlist,
    conset,
    constr,
)

from litestar.exceptions import HTTPException


class PetException(HTTPException):
    status_code = 406


class Gender(str, Enum):
    MALE = "M"
    FEMALE = "F"
    OTHER = "O"
    ANY = "A"


constrained_numbers = [
    conint(gt=10, lt=100),
    conint(ge=10, le=100),
    conint(ge=10, le=100, multiple_of=7),
    confloat(gt=10, lt=100),
    confloat(ge=10, le=100),
    confloat(ge=10, le=100, multiple_of=4.2),
    confloat(gt=10, lt=100, multiple_of=10),
    condecimal(gt=Decimal("10"), lt=Decimal("100")),
    condecimal(ge=Decimal("10"), le=Decimal("100")),
    condecimal(gt=Decimal("10"), lt=Decimal("100"), multiple_of=Decimal("5")),
    condecimal(ge=Decimal("10"), le=Decimal("100"), multiple_of=Decimal("2")),
]
constrained_string = [
    constr(regex="^[a-zA-Z]$") if pydantic.VERSION.startswith("1") else constr(pattern="^[a-zA-Z]$"),  # type: ignore[call-arg]
    constr(to_upper=True, min_length=1, regex="^[a-zA-Z]$")  # type: ignore[call-arg]
    if pydantic.VERSION.startswith("1")
    else constr(to_upper=True, min_length=1, pattern="^[a-zA-Z]$"),
    constr(to_lower=True, min_length=1, regex="^[a-zA-Z]$")  # type: ignore[call-arg]
    if pydantic.VERSION.startswith("1")
    else constr(to_lower=True, min_length=1, pattern="^[a-zA-Z]$"),
    constr(to_lower=True, min_length=10, regex="^[a-zA-Z]$")  # type: ignore[call-arg]
    if pydantic.VERSION.startswith("1")
    else constr(to_lower=True, min_length=10, pattern="^[a-zA-Z]$"),
    constr(to_lower=True, min_length=10, max_length=100, regex="^[a-zA-Z]$")  # type: ignore[call-arg]
    if pydantic.VERSION.startswith("1")
    else constr(to_lower=True, min_length=10, max_length=100, pattern="^[a-zA-Z]$"),
    constr(min_length=1),
    constr(min_length=10),
    constr(min_length=10, max_length=100),
    conbytes(min_length=1),
    conbytes(min_length=10),
    conbytes(min_length=10, max_length=100),
    conbytes(min_length=1),
    conbytes(min_length=10),
    conbytes(min_length=10, max_length=100),
]
constrained_collection = [
    conlist(int, min_items=1) if pydantic.VERSION.startswith("1") else conlist(int, min_length=1),  # type: ignore[call-arg]
    conlist(int, min_items=1, max_items=10)  # type: ignore[call-arg]
    if pydantic.VERSION.startswith("1")
    else conlist(int, min_length=1, max_length=10),
    conset(int, min_items=1) if pydantic.VERSION.startswith("1") else conset(int, min_length=1),  # type: ignore[call-arg]
    conset(int, min_items=1, max_items=10)  # type: ignore[call-arg]
    if pydantic.VERSION.startswith("1")
    else conset(int, min_length=1, max_length=10),
]
constrained_dates = [
    condate(gt=date.today() - timedelta(days=10), lt=date.today() + timedelta(days=100)),
    condate(ge=date.today() - timedelta(days=10), le=date.today() + timedelta(days=100)),
    condate(gt=date.today() - timedelta(days=10), lt=date.today() + timedelta(days=100)),
    condate(ge=date.today() - timedelta(days=10), le=date.today() + timedelta(days=100)),
]
