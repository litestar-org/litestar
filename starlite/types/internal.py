from typing import NamedTuple, Type


class PathParameterDefinition(NamedTuple):
    name: str
    full: str
    type: Type
