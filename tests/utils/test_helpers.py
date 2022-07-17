from typing import Any

from starlite.utils.helpers import ensure_unbound


def test_ensure_unbound_plain_fn() -> None:
    def f() -> None:
        ...

    assert ensure_unbound(f) is f


def test_ensure_unbound_fn_assigned_to_class_body() -> None:
    def f(arg: Any) -> None:
        ...

    class Test:
        fn = f

    assert ensure_unbound(Test().fn) is f


def test_ensure_unbound_assigned_to_instance() -> None:
    def f(arg: Any) -> None:
        ...

    class Test:
        fn: Any

    inst = Test()

    inst.fn = f

    assert ensure_unbound(inst.fn) is f
