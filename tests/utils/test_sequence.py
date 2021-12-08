import pytest

from starlite.utils.sequence import as_iterable, compact


@pytest.mark.parametrize("value, expected", [["123", ["123"]], [[], []], [(), ()], [1, [1]], [True, [True]]])
def test_as_iterable(value, expected):
    assert as_iterable(value) == expected


def test_compact():
    list_to_filter = [True, False, "str", "", 1, 0, None, {}, [], ()]
    assert compact(list_to_filter) == [True, "str", 1]
    assert compact(list_to_filter, none_only=True) == [v for v in list_to_filter if v is not None]
