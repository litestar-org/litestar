from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, fields
from typing import TYPE_CHECKING, Literal

from litestar._openapi.utils import default_operation_id_creator
from litestar.openapi.controller import OpenAPIController
from litestar.openapi.spec import (
    Components,
    Contact,
    ExternalDocumentation,
    Info,
    License,
    OpenAPI,
    PathItem,
    Reference,
    SecurityRequirement,
    Server,
    Tag,
)
from litestar.utils.path import normalize_path

__all__ = ("OpenAPIConfig",)


if TYPE_CHECKING:
    from litestar.types.callable_types import OperationIDCreator


@dataclass
class OpenAPIConfig:
    """Configuration for OpenAPI.

    To enable OpenAPI schema generation and serving, pass an instance of this class to the
    :class:`Litestar <.app.Litestar>` constructor using the ``openapi_config`` kwargs.
    """

    title: str
    """Title of API documentation."""
    version: str
    """API version, e.g. '1.0.0'."""

    create_examples: bool = field(default=False)
    """Generate examples using the polyfactory library."""
    openapi_controller: type[OpenAPIController] = field(default_factory=lambda: OpenAPIController)
    """Controller for generating OpenAPI routes.

    Must be subclass of :class:`OpenAPIController <litestar.openapi.controller.OpenAPIController>`.
    """
    contact: Contact | None = field(default=None)
    """API contact information, should be an :class:`Contact <litestar.openapi.spec.contact.Contact>` instance."""
    description: str | None = field(default=None)
    """API description."""
    external_docs: ExternalDocumentation | None = field(default=None)
    """Links to external documentation.

    Should be an instance of :class:`ExternalDocumentation <litestar.openapi.spec.external_documentation.ExternalDocumentation>`.
    """
    license: License | None = field(default=None)
    """API Licensing information.

    Should be an instance of :class:`License <litestar.openapi.spec.license.License>`.
    """
    security: list[SecurityRequirement] | None = field(default=None)
    """API Security requirements information.

    Should be an instance of
        :data:`SecurityRequirement <.openapi.spec.SecurityRequirement>`.
    """
    components: Components | list[Components] = field(default_factory=Components)
    """API Components information.

    Should be an instance of :class:`Components <litestar.openapi.spec.components.Components>` or a list thereof.
    """
    servers: list[Server] = field(default_factory=lambda: [Server(url="/")])
    """A list of :class:`Server <litestar.openapi.spec.server.Server>` instances."""
    summary: str | None = field(default=None)
    """A summary text."""
    tags: list[Tag] | None = field(default=None)
    """A list of :class:`Tag <litestar.openapi.spec.tag.Tag>` instances."""
    terms_of_service: str | None = field(default=None)
    """URL to page that contains terms of service."""
    use_handler_docstrings: bool = field(default=False)
    """Draw operation description from route handler docstring if not otherwise provided."""
    webhooks: dict[str, PathItem | Reference] | None = field(default=None)
    """A mapping of key to either :class:`PathItem <litestar.openapi.spec.path_item.PathItem>` or.

    :class:`Reference <litestar.openapi.spec.reference.Reference>` objects.
    """
    root_schema_site: Literal["redoc", "swagger", "elements", "rapidoc"] = "redoc"
    """The static schema generator to use for the "root" path of `/schema/`."""
    enabled_endpoints: set[str] = field(
        default_factory=lambda: {
            "redoc",
            "swagger",
            "elements",
            "rapidoc",
            "openapi.json",
            "openapi.yaml",
            "openapi.yml",
            "oauth2-redirect.html",
        }
    )
    """A set of the enabled documentation sites and schema download endpoints."""
    operation_id_creator: OperationIDCreator = default_operation_id_creator
    """A callable that generates unique operation ids"""
    path: str | None = field(default=None)
    """Base path for the OpenAPI documentation endpoints."""

    def __post_init__(self) -> None:
        if self.path:
            self.path = normalize_path(self.path)
            self.openapi_controller = type("OpenAPIController", (self.openapi_controller,), {"path": self.path})

    def to_openapi_schema(self) -> OpenAPI:
        """Return an ``OpenAPI`` instance from the values stored in ``self``.

        Returns:
            An instance of :class:`OpenAPI <litestar.openapi.spec.open_api.OpenAPI>`.
        """

        if isinstance(self.components, list):
            merged_components = Components()
            for components in self.components:
                for key in (f.name for f in fields(components)):
                    if value := getattr(components, key, None):
                        merged_value_dict = getattr(merged_components, key, {}) or {}
                        merged_value_dict.update(value)
                        setattr(merged_components, key, merged_value_dict)

            self.components = merged_components

        return OpenAPI(
            external_docs=self.external_docs,
            security=self.security,
            components=deepcopy(self.components),  # deepcopy prevents mutation of the config's components
            servers=self.servers,
            tags=self.tags,
            webhooks=self.webhooks,
            info=Info(
                title=self.title,
                version=self.version,
                description=self.description,
                contact=self.contact,
                license=self.license,
                summary=self.summary,
                terms_of_service=self.terms_of_service,
            ),
            paths={},
        )
