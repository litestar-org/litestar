from __future__ import annotations

import dataclasses
from types import TracebackType

from starlite.exceptions import MissingDependencyException


@dataclasses.dataclass
class Feature:
    name: str
    available_in_extras: tuple[str, ...]

    def __enter__(self) -> None:
        return None

    def __exit__(self, exc_type: type[BaseException], exc_val: BaseException, exc_tb: TracebackType) -> None:
        """Handle import errors of optional dependencies."""
        if isinstance(exc_val, ImportError):
            raise MissingDependencyException(self.name, self.available_in_extras)


SQLALCHEMY = Feature("SQLAlchemyPlugin", ("sqlalchemy", "all"))
JINJA = Feature("jinja2 templates", ("jinja2",))
MAKO = Feature("mako templates", ("mako",))
TESTING = Feature("starlite.testing", ("testing", "all"))
YAML = Feature("OpenAPI YAML format", ("yaml", "all"))
PYDANTIC_FACTORIES = Feature("pydantic-factories", ("pydantic-factories",))
