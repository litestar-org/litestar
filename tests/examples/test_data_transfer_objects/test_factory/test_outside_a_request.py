from msgspec import to_builtins


def test_outside_a_request() -> None:
    from docs.examples.data_transfer_objects.factory.outside_a_request import (
        User,
        from_msgpack,
        same_user,
        transfer,
        user,
    )

    assert user == User(name="Mr Sunglass", email="mr.sunglass@example.com", password="secret")
    assert same_user == from_msgpack == User(name="Mr Sunglass", email="mr.sunglass@example.com")
    assert to_builtins(transfer) == {"name": "Mr Sunglass", "email": "mr.sunglass@example.com"}
