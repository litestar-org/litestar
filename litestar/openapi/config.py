from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass, field, fields
from typing import TYPE_CHECKING

from litestar._openapi.utils import (
    default_operation_id_creator,
    default_schema_component_name_creator,
    supports_openapi_3_2,
)
from litestar.exceptions import ImproperlyConfiguredException
from litestar.openapi.plugins import ScalarRenderPlugin
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

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from litestar.openapi.datastructures import ResponseSpec
    from litestar.openapi.plugins import OpenAPIRenderPlugin
    from litestar.router import Router
    from litestar.types.callable_types import OperationIDCreator
    from litestar.typing import FieldDefinition

__all__ = ("OpenAPIConfig",)


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
    random_seed: int = 10
    """The random seed used when creating the examples to ensure deterministic generation of examples."""
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
    operation_id_creator: OperationIDCreator = default_operation_id_creator
    """A callable that generates unique operation ids"""
    path: str = "/schema"
    """Base path for the OpenAPI documentation endpoints.

    If no path is provided the default is ``/schema``.

    Ignored if :attr:`openapi_router` is provided.
    """
    render_plugins: Sequence[OpenAPIRenderPlugin] = field(default=(ScalarRenderPlugin(),))
    """Plugins for rendering OpenAPI documentation UIs.

    .. versionchanged:: 3.0.0

        Default behavior changed to serve only :class:`ScalarRenderPlugin`.
    """
    openapi_router: Router | None = None
    """An optional router for serving OpenAPI documentation and schema files.

    If provided, ``path`` is ignored.

    :attr:`openapi_router` is not required, but it can be passed to customize the configuration of the router used to
    serve the documentation endpoints. For example, you can add middleware or guards to the router.

    Handlers to serve the OpenAPI schema and documentation sites are added to this router according to
    :attr:`render_plugins`, so routes shouldn't be added that conflict with these.
    """
    openapi_version: str = "3.1.0"
    """The version of the OpenAPI Specification the generated document conforms to.

    Set to ``"3.2.0"`` to generate an OpenAPI 3.2 document. Fields documented as requiring OpenAPI 3.2 are only valid
    in such a document, and tooling support for it is not as widespread as for 3.1.

    .. versionadded:: 3.0.0
    """
    self_uri: str | None = None
    """The URI of the generated document, emitted as ``$self``. Requires OpenAPI 3.2.

    .. versionadded:: 3.0.0
    """
    schema_component_name_creator: Callable[[FieldDefinition], str] = default_schema_component_name_creator
    """A callable that receives the :class:`FieldDefinition <litestar.typing.FieldDefinition>` of a type and returns
    the name of its schema in the ``components/schemas`` section.

    Characters that are not allowed in a component name are replaced with ``_``. If the same name is returned for
    different types, the names are told apart by the modules the types are defined in.

    .. versionadded:: 3.0.0
    """
    error_response: ResponseSpec | None = None
    """A :class:`ResponseSpec <litestar.openapi.datastructures.ResponseSpec>` describing the content of error responses.

    Applied to the responses generated for the exceptions in a route handler's ``raises`` and for the validation error
    of an operation that receives parameters or a request body. Set this if the application does not return Litestar's
    default exception response, for example because of custom ``exception_handlers``. The description of each response
    is still derived from its exceptions, ``description`` of the spec is not used. Examples are only generated if
    :attr:`create_examples` is enabled as well. Entries in the ``responses`` of a route handler take precedence.

    .. versionadded:: 3.0.0
    """

    def __post_init__(self) -> None:
        self.path = normalize_path(self.path)

        if not re.fullmatch(r"3\.[12]\.\d+", self.openapi_version):
            raise ImproperlyConfiguredException(
                f"Unsupported OpenAPI version {self.openapi_version!r}. Supported versions are 3.1.x and 3.2.x"
            )
        if self.self_uri is not None and not supports_openapi_3_2(self.openapi_version):
            raise ImproperlyConfiguredException("'self_uri' requires 'openapi_version' to be 3.2.0 or newer")

        self.default_plugin: OpenAPIRenderPlugin | None = None
        for plugin in self.render_plugins:
            if plugin.has_path("/"):
                self.default_plugin = plugin
                break
        else:
            if self.render_plugins:
                self.default_plugin = self.render_plugins[0]

    def get_path(self) -> str:
        return self.openapi_router.path if self.openapi_router else self.path

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
            openapi=self.openapi_version,
            self_uri=self.self_uri,
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
