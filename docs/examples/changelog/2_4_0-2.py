from dataclasses import dataclass


@dataclass
class Bar:
    id: str


@dataclass
class Foo:
    id: str
    bar: Bar


FooDTO = DataclassDTO[Annotated[Foo, DTOConfig(rename_fields={"id": "foo_id"})]]