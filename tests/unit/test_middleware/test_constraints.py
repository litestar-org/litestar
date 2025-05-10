from typing import Any

import pytest

from litestar.middleware.base import ASGIMiddleware
from litestar.middleware.constraints import CycleError, MiddlewareConstraints, check_middleware_constraints
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


def test_constraint_ignore_not_found() -> None:
    constraints = (
        MiddlewareConstraints()
        .apply_after("SomethingNotAvailable", ignore_not_found=True)
        .apply_before("SomethingNotAvailable", ignore_not_found=True)
    )
    resolved = constraints.resolve()
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

    with pytest.raises(ValueError, match="MiddlewareTwo.*before.*MiddlewareOne"):
        check_middleware_constraints(middlewares)


def test_order_after() -> None:
    one = MiddlewareOne()
    two = MiddlewareTwo()
    three = MiddlewareThree()

    two.constraints = MiddlewareConstraints(after=(MiddlewareOne,))

    middlewares = (two, one, three)

    with pytest.raises(ValueError, match="MiddlewareTwo.*after.*MiddlewareOne"):
        check_middleware_constraints(middlewares)


def test_order_string_ref() -> None:
    one = MiddlewareOne()
    two = MiddlewareTwo()
    three = MiddlewareThree()

    two.constraints = MiddlewareConstraints().apply_before(fully_qualified_name(MiddlewareOne))

    middlewares = (one, two, three)

    with pytest.raises(ValueError, match="MiddlewareTwo.*before.*MiddlewareOne"):
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

    with pytest.raises(ValueError, match="MiddlewareOne.*after.*middleware_factory"):
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

    with pytest.raises(ValueError, match="MiddlewareOne.*before.*middleware_factory"):
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

    with pytest.raises(ValueError, match="MiddlewareOne.*before.*middleware_factory"):
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
    with pytest.raises(ValueError, match="MiddlewareTwo.*after.*MiddlewareOne"):
        check_middleware_constraints(given)


@pytest.mark.parametrize("constraint", ["before", "after"])
def test_order_multiple_instances_referer(constraint: str) -> None:
    # check priority works in all cases if more than one instances of the referring
    # middleware (i.e. the one defining the priority) is present
    one = MiddlewareOne()
    two_one = MiddlewareTwo()
    two_two = MiddlewareTwo()
    two_one.constraints = two_two.constraints = MiddlewareConstraints(**{constraint: (MiddlewareOne,)})

    given = (
        two_one,
        one,
        two_two,
    )

    with pytest.raises(ValueError, match=f"MiddlewareTwo.*{constraint}.*MiddlewareOne"):
        check_middleware_constraints(given)


@pytest.mark.parametrize("constraint", ["before", "after"])
def test_order_multiple_instances_referee(constraint: str) -> None:
    # check priority works in all cases if more than one instances of the referenced
    # middleware (i.e. the one referenced in the priority) is present
    one_one = MiddlewareOne()
    one_two = MiddlewareOne()
    two = MiddlewareTwo()
    two.constraints = MiddlewareConstraints(**{constraint: (MiddlewareOne,)})

    given = (
        one_one,
        two,
        one_two,
    )

    with pytest.raises(ValueError, match=f"MiddlewareTwo.*{constraint}.*MiddlewareOne"):
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
    with pytest.raises(ValueError, match="MiddlewareTwo.*before.*MiddlewareOne"):
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
