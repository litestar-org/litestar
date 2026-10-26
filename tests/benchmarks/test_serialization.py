"""Serialization and DTO benchmarks."""

from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.serialization import decode_json, encode_json, get_serializer
from tests.benchmarks.apps import PEOPLE, Person

if TYPE_CHECKING:
    from pytest_codspeed import BenchmarkFixture


def test_encode_json_structs(benchmark: BenchmarkFixture) -> None:
    serializer = get_serializer()
    result = benchmark(encode_json, PEOPLE, serializer)
    assert result.startswith(b"[")


def test_decode_json_typed(benchmark: BenchmarkFixture) -> None:
    data = encode_json(PEOPLE)
    result = benchmark(decode_json, data, list[Person])
    assert len(result) == len(PEOPLE)


def test_decode_json_untyped(benchmark: BenchmarkFixture) -> None:
    data = encode_json(PEOPLE)
    result = benchmark(decode_json, data)
    assert len(result) == len(PEOPLE)
