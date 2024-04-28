from dataclasses import dataclass


@dataclass
class Bar:
    id: str


@dataclass
class Foo:
    id: str
    bars: list[Bar]


FooDTO = DataclassDTO[Annotated[Foo, DTOConfig(rename_fields={"bars.0.id": "bar_id"})]]
