from __future__ import annotations

from starlite._signature.parsing import create_signature_model

from . import ConcreteDTO, Model


def test_create_signature_model() -> None:
    def func(data: ConcreteDTO[Model]) -> None:
        ...

    signature_model = create_signature_model(
        func, plugins=[], dependency_name_set=set(), namespace={"ConcreteDTO": ConcreteDTO, "Model": Model}
    )
    assert signature_model.fields["data"].has_dto_annotation
