from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from litestar.openapi.spec.base import BaseSchemaObject

if TYPE_CHECKING:
    from litestar.openapi.spec.external_documentation import ExternalDocumentation

__all__ = ("Tag",)


@dataclass
class Tag(BaseSchemaObject):
    """Adds metadata to a single tag that is used by the
    `Operation Object <https://spec.openapis.org/oas/v3.1.0#operationObject>`_.

    It is not mandatory to have a Tag Object per tag defined in the Operation Object instances.
    """

    name: str
    """**REQUIRED**. The name of the tag."""

    description: str | None = None
    """A short description for the tag.

    `CommonMark syntax <https://spec.commonmark.org/>`_ MAY be used for rich text representation.
    """

    external_docs: ExternalDocumentation | None = None
    """Additional external documentation for this tag."""

    summary: str | None = None
    """A short summary of the tag, used for display purposes.

    Requires OpenAPI 3.2.
    """

    parent: str | None = None
    """The ``name`` of a tag that this tag is nested under. The named tag MUST exist in the document, and circular
    references between parent and child tags MUST NOT be used.

    Requires OpenAPI 3.2.
    """

    kind: str | None = None
    """A machine-readable string to categorize what sort of tag it is, e.g. ``nav``, ``badge`` or ``audience``.

    Requires OpenAPI 3.2.
    """
