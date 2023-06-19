from litestar.utils.sequence import find_index, unique


def test_find_index() -> None:
    assert find_index([1, 2], lambda x: x == 2) == 1
    assert find_index([1, 3], lambda x: x == 2) == -1


def test_unique() -> None:
    assert unique([1, 1, 1, 2]) == [1, 2]

    def x() -> None:
        pass

    def y() -> None:
        pass

    unique_functions = unique([x, x, y, y])
    assert unique_functions == [x, y] or [y, x]
    my_list: list = []
    assert sorted(unique([my_list, my_list, my_list])) == sorted([my_list])
