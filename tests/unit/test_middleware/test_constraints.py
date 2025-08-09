from typing import Any

import pytest

from litestar.middleware.base import ASGIMiddleware
from litestar.middleware.constraints import (
    ConstraintViolationError,
    CycleError,
    MiddlewareConstraintError,
    MiddlewareConstraints,
    check_middleware_constraints,
)
from litestar.types import ASGIApp, Receive, Scope, Send


def fully_qualified_name(obj: Any) -> str:
    return f"{obj.__module__}.{obj.__qualname__}"


# place these here so they are importable


class MiddlewareOne(ASGIMiddleware):
    async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
        pass


class MiddlewareTwo(ASGIMiddleware):
    async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
        pass


class MiddlewareThree(ASGIMiddleware):
    async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
        pass


def middleware_factory(app: ASGIApp) -> ASGIApp:
    async def wrapped_app(scope: Scope, receive: Receive, send: Send) -> None:
        pass

    return wrapped_app


def test_constraint_ignore_import_error() -> None:
    constraints = (
        MiddlewareConstraints()
        .apply_after("SomethingNotAvailable", ignore_import_error=True)
        .apply_before("SomethingNotAvailable", ignore_import_error=True)
    )
    resolved = constraints._resolve()
    assert resolved.after == ()
    assert resolved.before == ()


def test_order_before() -> None:
    one = MiddlewareOne()
    two = MiddlewareTwo()
    three = MiddlewareThree()

    two.constraints = MiddlewareConstraints(before=(MiddlewareOne,))

    middlewares = (
        one,
        two,
        three,
    )

    with pytest.raises(ConstraintViolationError, match="MiddlewareTwo.*before.*MiddlewareOne"):
        check_middleware_constraints(middlewares)


def test_order_before_referenced_not_used() -> None:
    one = MiddlewareOne()
    two = MiddlewareTwo()

    two.constraints = MiddlewareConstraints(before=(MiddlewareThree,))

    check_middleware_constraints((one, two))


def test_order_before_ok() -> None:
    one = MiddlewareOne()
    two = MiddlewareTwo()
    three = MiddlewareThree()

    two.constraints = MiddlewareConstraints(before=(MiddlewareOne,))

    middlewares = (
        two,
        one,
        three,
    )

    check_middleware_constraints(middlewares)


def test_order_after() -> None:
    one = MiddlewareOne()
    two = MiddlewareTwo()
    three = MiddlewareThree()

    two.constraints = MiddlewareConstraints(after=(MiddlewareOne,))

    middlewares = (two, one, three)

    with pytest.raises(ConstraintViolationError, match="MiddlewareTwo.*after.*MiddlewareOne"):
        check_middleware_constraints(middlewares)


def test_order_after_referenced_not_used() -> None:
    one = MiddlewareOne()
    two = MiddlewareTwo()

    two.constraints = MiddlewareConstraints(after=(MiddlewareThree,))

    check_middleware_constraints((one, two))


def test_order_after_ok() -> None:
    one = MiddlewareOne()
    two = MiddlewareTwo()
    three = MiddlewareThree()

    two.constraints = MiddlewareConstraints(after=(MiddlewareOne,))

    middlewares = (
        one,
        two,
        three,
    )

    check_middleware_constraints(middlewares)


def test_order_string_ref() -> None:
    one = MiddlewareOne()
    two = MiddlewareTwo()
    three = MiddlewareThree()

    two.constraints = MiddlewareConstraints().apply_before(fully_qualified_name(MiddlewareOne))

    middlewares = (one, two, three)

    with pytest.raises(ConstraintViolationError, match="MiddlewareTwo.*before.*MiddlewareOne"):
        check_middleware_constraints(middlewares)


def test_order_function_after() -> None:
    one = MiddlewareOne()
    two = MiddlewareTwo()
    one.constraints = MiddlewareConstraints(after=(middleware_factory,))

    given = (
        one,
        two,
        middleware_factory,
    )

    with pytest.raises(ConstraintViolationError, match="MiddlewareOne.*after.*middleware_factory"):
        check_middleware_constraints(given)


def test_order_function_before() -> None:
    one = MiddlewareOne()
    two = MiddlewareTwo()

    one.constraints = MiddlewareConstraints(before=(middleware_factory,))

    given = (
        middleware_factory,
        one,
        two,
    )

    with pytest.raises(ConstraintViolationError, match="MiddlewareOne.*before.*middleware_factory"):
        check_middleware_constraints(given)


def test_order_function_string_ref() -> None:
    one = MiddlewareOne()
    two = MiddlewareTwo()
    given = (
        middleware_factory,
        one,
        two,
    )

    one.constraints = MiddlewareConstraints(before=(middleware_factory,))

    with pytest.raises(ConstraintViolationError, match="MiddlewareOne.*before.*middleware_factory"):
        check_middleware_constraints(given)


def test_order_multi_priority() -> None:
    one = MiddlewareOne()
    two = MiddlewareTwo()
    three = MiddlewareThree()
    two.constraints = MiddlewareConstraints(after=(MiddlewareOne,))
    three.constraints = MiddlewareConstraints(before=(MiddlewareTwo,))

    given = (
        two,
        one,
        three,
    )

    # expect the first violation (two -> one) to be reported
    with pytest.raises(ConstraintViolationError, match="MiddlewareTwo.*after.*MiddlewareOne"):
        check_middleware_constraints(given)


@pytest.mark.parametrize("constraint", ["before", "after"])
def test_order_multiple_instances_referer(constraint: str) -> None:
    # check priority works in all cases if more than one instances of the referring
    # middleware (i.e. the one defining the priority) is present
    one = MiddlewareOne()
    two_one = MiddlewareTwo()
    two_two = MiddlewareTwo()
    two_one.constraints = two_two.constraints = MiddlewareConstraints(**{constraint: (MiddlewareOne,)})  # type: ignore[arg-type]

    given = (
        two_one,
        one,
        two_two,
    )

    with pytest.raises(ConstraintViolationError, match=f"MiddlewareTwo.*{constraint}.*MiddlewareOne"):
        check_middleware_constraints(given)


@pytest.mark.parametrize("constraint", ["before", "after"])
def test_order_multiple_instances_referee(constraint: str) -> None:
    # check priority works in all cases if more than one instances of the referenced
    # middleware (i.e. the one referenced in the priority) is present
    one_one = MiddlewareOne()
    one_two = MiddlewareOne()
    two = MiddlewareTwo()
    two.constraints = MiddlewareConstraints(**{constraint: (MiddlewareOne,)})  # type: ignore[arg-type]

    given = (
        one_one,
        two,
        one_two,
    )

    with pytest.raises(ConstraintViolationError, match=f"MiddlewareTwo.*{constraint}.*MiddlewareOne"):
        check_middleware_constraints(given)


def test_order_subclass() -> None:
    # if a base class of a middleware is referenced, its priority should apply to all
    # subclasses
    class SubclassOfOne(MiddlewareOne):
        pass

    class CustomBaseClass:
        pass

    class CustomSubClass(CustomBaseClass):
        pass

    subclass_of_one = SubclassOfOne()
    one = MiddlewareOne()
    two = MiddlewareTwo()
    three = MiddlewareThree()
    custom_sub_class = CustomSubClass()

    two.constraints = MiddlewareConstraints(before=(MiddlewareOne,))
    three.constraints = MiddlewareConstraints(after=(CustomBaseClass,))  # type: ignore[arg-type]

    given = (
        one,
        subclass_of_one,
        two,
        three,
        custom_sub_class,
    )

    # expect the first constraint to be violated
    with pytest.raises(ConstraintViolationError, match="MiddlewareTwo.*before.*MiddlewareOne"):
        check_middleware_constraints(given)  # type: ignore[arg-type]


def test_order_handle_cycle() -> None:
    one = MiddlewareOne()
    two = MiddlewareTwo()
    one.constraints = MiddlewareConstraints(before=(MiddlewareTwo,))
    two.constraints = MiddlewareConstraints(before=(MiddlewareOne,))

    # TODO: Handle cycle error to point to specific instances
    with pytest.raises(CycleError):
        check_middleware_constraints((one, two))


def test_order_handle_self_referential() -> None:
    one = MiddlewareOne()
    one.constraints = MiddlewareConstraints(before=(MiddlewareOne,))

    with pytest.raises(CycleError):
        check_middleware_constraints((one,))


def test_first() -> None:
    one = MiddlewareOne()
    two = MiddlewareTwo()
    one.constraints = MiddlewareConstraints(first=True)

    with pytest.raises(
        ConstraintViolationError,
        match=r"MiddlewareOne'.* is required to be in the first position, but was found at index 1. \(Violates constraint 'first=True'\)",
    ):
        check_middleware_constraints((two, one))


def test_first_subclass() -> None:
    MiddlewareOne.constraints = MiddlewareConstraints(first=True)

    class SubOne(MiddlewareOne):
        pass

    one = SubOne()
    two = MiddlewareTwo()

    with pytest.raises(
        ConstraintViolationError,
        match=r"SubOne.* is required to be in the first position, but was found at index 1. \(Violates constraint 'first=True'\)",
    ):
        check_middleware_constraints((two, one))


def test_first_ok() -> None:
    one = MiddlewareOne()
    two = MiddlewareTwo()
    one.constraints = MiddlewareConstraints(first=True)

    check_middleware_constraints((one, two))


def test_multiple_first() -> None:
    one = MiddlewareOne()
    two = MiddlewareTwo()
    one.constraints = MiddlewareConstraints(first=True)
    two.constraints = MiddlewareConstraints(first=True)

    with pytest.raises(
        MiddlewareConstraintError, match="Multiple middlewares define 'first=True':.*MiddlewareOne, .*MiddlewareTwo"
    ):
        check_middleware_constraints((one, two))


def test_last() -> None:
    one = MiddlewareOne()
    two = MiddlewareTwo()
    one.constraints = MiddlewareConstraints(last=True)

    with pytest.raises(
        ConstraintViolationError,
        match=r"MiddlewareOne.*is required to be in the last position \(index 1 of 1\), but was found at index 0. \(Violates constraint 'last=True'\)",
    ):
        check_middleware_constraints((one, two))


def test_last_subclass() -> None:
    MiddlewareOne.constraints = MiddlewareConstraints(last=True)

    class SubOne(MiddlewareOne):
        pass

    one = SubOne()
    two = MiddlewareTwo()

    with pytest.raises(
        ConstraintViolationError,
        match=r"SubOne'.* is required to be in the last position \(index 1 of 1\), but was found at index 0. \(Violates constraint 'last=True'\)",
    ):
        check_middleware_constraints((one, two))


def test_last_ok() -> None:
    one = MiddlewareOne()
    two = MiddlewareTwo()
    one.constraints = MiddlewareConstraints(last=True)

    check_middleware_constraints((two, one))


def test_multiple_last() -> None:
    one = MiddlewareOne()
    two = MiddlewareTwo()
    one.constraints = MiddlewareConstraints(last=True)
    two.constraints = MiddlewareConstraints(last=True)

    with pytest.raises(
        MiddlewareConstraintError, match="Multiple middlewares define 'last=True':.*MiddlewareOne, .*MiddlewareTwo"
    ):
        check_middleware_constraints((one, two))


def test_unique() -> None:
    one = MiddlewareOne()
    one_two = MiddlewareOne()
    two = MiddlewareTwo()
    one.constraints = MiddlewareConstraints(unique=True)

    with pytest.raises(
        ConstraintViolationError, match=r"MiddlewareOne.*must be unique. Found 2 instances \(indices 0, 2\)"
    ):
        check_middleware_constraints((one, two, one_two))


def test_unique_subclass() -> None:
    MiddlewareOne.constraints = MiddlewareConstraints(unique=True)

    class SubOne(MiddlewareOne):
        pass

    one = SubOne()
    one_two = MiddlewareOne()
    two = MiddlewareTwo()

    with pytest.raises(
        ConstraintViolationError, match=r"MiddlewareOne.*must be unique. Found 2 instances \(indices 0, 2\)"
    ):
        check_middleware_constraints((one, two, one_two))


def test_unique_multi() -> None:
    one_one = MiddlewareOne()
    one_two = MiddlewareOne()
    two = MiddlewareTwo()
    three_one = MiddlewareThree()
    three_two = MiddlewareThree()
    one_one.constraints = one_two.constraints = MiddlewareConstraints(unique=True)
    three_one.constraints = three_one.constraints = MiddlewareConstraints(unique=True)

    with pytest.raises(
        ConstraintViolationError, match=r"MiddlewareOne.*must be unique. Found 2 instances \(indices 0, 1\)"
    ):
        check_middleware_constraints((one_one, one_two, two, three_one, three_two))


def test_unique_ok() -> None:
    one = MiddlewareOne()
    two = MiddlewareTwo()
    one.constraints = MiddlewareConstraints(unique=False)

    check_middleware_constraints((one, two))


@pytest.mark.parametrize(
    "options,expected_exception",
    [
        ({"first": True, "last": True}, "Cannot set 'first=True' if 'last=True'"),
        ({"first": True, "unique": False}, "Cannot set 'first=True' if 'unique=False'"),
        ({"first": True, "after": ("something",)}, "Cannot set 'first=True' if if 'after' is not empty"),
        ({"last": True, "unique": False}, "Cannot set 'last=True' if 'unique=False'"),
        ({"last": True, "before": ("something",)}, "Cannot set 'last=True' if 'before' is not empty"),
    ],
)
def test_mutually_exclusive_options(options: dict[str, bool], expected_exception: str) -> None:
    with pytest.raises(MiddlewareConstraintError, match=expected_exception):
        MiddlewareConstraints(**options)  # type: ignore[arg-type]


def test_require_unique() -> None:
    assert MiddlewareConstraints(unique=False).require_unique(True).unique is True
    assert MiddlewareConstraints(unique=True).require_unique(False).unique is False


def test_apply_first() -> None:
    constraints = MiddlewareConstraints().apply_first()
    assert constraints == MiddlewareConstraints(first=True, last=False, unique=True)


def test_apply_last() -> None:
    constraints = MiddlewareConstraints().apply_last()
    assert constraints == MiddlewareConstraints(last=True, first=False, unique=True)


def test_apply_before() -> None:
    constraints = MiddlewareConstraints().apply_before(MiddlewareOne)
    assert constraints == MiddlewareConstraints(before=(MiddlewareOne,))


def test_apply_after() -> None:
    constraints = MiddlewareConstraints().apply_after(MiddlewareOne)
    assert constraints == MiddlewareConstraints(after=(MiddlewareOne,))
