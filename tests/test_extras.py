import pytest

from starlite import MissingDependencyException
from starlite.extras import Feature


def test_feature() -> None:
    sample_feature = Feature("Some Feature", ("some-extra",))

    with pytest.raises(MissingDependencyException) as ctx:  # noqa: SIM117
        with sample_feature:
            import non_existing  # noqa: F401

    expected_message = (
        "To use Some Feature, install starlite with 'some-extra' extra:\n"
        "e.g. `pip install starlite[some-extra]`\n"
        "or `poetry add starlite --extras some-extra`"
    )
    assert str(ctx.value) == expected_message
    assert repr(ctx.value) == f"MissingDependencyException({expected_message!r})"


def test_feature_with_multiple_extras() -> None:
    sample_feature = Feature("Some Feature", ("some-extra",))

    with pytest.raises(MissingDependencyException) as ctx:  # noqa: SIM117
        with sample_feature:
            import non_existing  # noqa: F401

    expected_message = (
        "To use Some Feature, install starlite with 'some-extra' extra:\n"
        "e.g. `pip install starlite[some-extra]`\n"
        "or `poetry add starlite --extras some-extra`"
    )
    assert str(ctx.value) == expected_message
    assert repr(ctx.value) == f"MissingDependencyException({expected_message!r})"
