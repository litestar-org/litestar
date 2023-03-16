from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from starlite.openapi.spec.base import BaseSchemaObject

if TYPE_CHECKING:
    from starlite.openapi.spec.external_documentation import ExternalDocumentation

__all__ = ("Tag",)


@dataclass
class Tag(BaseSchemaObject):
    """Adds metadata to a single tag that is used by the [Operation
    Object](https://spec.openapis.org/oas/v3.1.0#operationObject).

    It is not mandatory to have a Tag Object per tag defined in the
    Operation Object instances.
    """

    name: str
    """
    **REQUIRED**. The name of the tag.
    """

    description: str | None = None
    """A short description for the tag.

    [CommonMark syntax](https://spec.commonmark.org/) MAY be used for
    rich text representation.
    """

    external_docs: ExternalDocumentation | None = None
    """Additional external documentation for this tag."""
