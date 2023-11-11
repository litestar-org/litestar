from dataclasses import dataclass


@dataclass
class Form:
    name: str
    age: int
    programmer: bool
    value: str
