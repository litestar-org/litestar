from datetime import date, datetime, time, timedelta
from typing import Any

import pytest

from starlite._signature.models.attrs_signature_model import _converter
from tests import Person, PersonFactory

now = datetime.now()
today = date.today()
time_now = time(hour=now.hour, minute=now.minute, second=now.second, microsecond=now.microsecond)
one_minute = timedelta(minutes=1)
person = PersonFactory.build()


@pytest.mark.parametrize(
    "value,cls,expected",
    (
        (now, datetime, now.isoformat()),
        (now.timestamp(), datetime, now.isoformat()),
        (now.isoformat(), datetime, now.isoformat()),
    ),
)
def test_cattrs_converter_structure_datetime(value: Any, cls: Any, expected: Any) -> None:
    result = _converter.structure(value, cls).isoformat()
    assert result == expected


@pytest.mark.parametrize(
    "value,cls,expected",
    (
        (now, date, today.isoformat()),
        (now.isoformat(), date, today.isoformat()),
        (now.timestamp(), date, today.isoformat()),
        (today, date, today.isoformat()),
        (today.isoformat(), date, today.isoformat()),
    ),
)
def test_cattrs_converter_structure_date(value: Any, cls: Any, expected: Any) -> None:
    result = _converter.structure(value, cls).isoformat()
    assert result == expected


@pytest.mark.parametrize(
    "value,cls,expected",
    (
        (time_now, time, time_now.isoformat()),
        (time_now.isoformat(), time, time_now.isoformat()),
        (now.timestamp(), time, time_now.isoformat()),
    ),
)
def test_cattrs_converter_structure_time(value: Any, cls: Any, expected: Any) -> None:
    result = _converter.structure(value, cls).isoformat()
    assert result == expected


@pytest.mark.parametrize(
    "value,cls,expected",
    (
        (one_minute, timedelta, one_minute.total_seconds()),
        (one_minute.total_seconds(), timedelta, one_minute.total_seconds()),
        ("1 minute", timedelta, one_minute.total_seconds()),
    ),
)
def test_cattrs_converter_structure_timedelta(value: Any, cls: Any, expected: Any) -> None:
    result = _converter.structure(value, cls).total_seconds()
    assert result == expected


@pytest.mark.parametrize(
    "value,cls,expected",
    (
        (person, Person, person.dict()),
        (person.dict(), Person, person.dict()),
    ),
)
def test_cattrs_converter_structure_pydantic(value: Any, cls: Any, expected: Any) -> None:
    result = _converter.structure(value, cls).dict()
    assert result == expected
