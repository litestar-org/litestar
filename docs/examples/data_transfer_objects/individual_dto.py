from dataclasses import dataclass
from litestar.dto import DTOConfig, DataclassDTO


@dataclass
class Foo:
    name: str


class FooDTO(DataclassDTO[Foo]):
    config = DTOConfig(experimental_codegen_backend=True)