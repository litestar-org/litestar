from typing import (
    TYPE_CHECKING,
    Any,
    AsyncContextManager,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Union,
)

from openapi_schema_pydantic import (
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
from pydantic import AnyUrl
from starlette.applications import Starlette
from starlette.datastructures import State
from starlette.middleware import Middleware
from typing_extensions import Type

from starlite.enums import OpenAPIMediaType
from starlite.handlers import RouteHandler
from starlite.logging import LoggingConfig
from starlite.provide import Provide
from starlite.routing import RootRouter, Router
from starlite.utils import DeprecatedProperty

if TYPE_CHECKING:  # pragma: no cover
    from starlite.controller import Controller


# noinspection PyMethodOverriding
class Starlite(Starlette):
    def __init__(  # pylint: disable=super-init-not-called, too-many-locals
        self,
        *,
        debug: bool = False,
        middleware: Sequence[Middleware] = None,
        exception_handlers: Dict[Union[int, Type[Exception]], Callable] = None,
        route_handlers: Optional[Sequence[Union[Type["Controller"], RouteHandler, Router, Callable]]] = None,
        on_startup: Optional[Sequence[Callable]] = None,
        on_shutdown: Optional[Sequence[Callable]] = None,
        lifespan: Optional[Callable[[Any], AsyncContextManager]] = None,
        dependencies: Optional[Dict[str, Provide]] = None,
        logging_config: Optional[LoggingConfig] = LoggingConfig(),
        # openapi config below
        openapi_schema_url: str = "/schema",
        openapi_media_type: OpenAPIMediaType = OpenAPIMediaType.OPENAPI_YAML,
        title: str = "StarLite API",
        version: str = "1.0.0",
        contact: Optional[Contact] = None,
        description: Optional[str] = None,
        external_docs: Optional[ExternalDocumentation] = None,
        license: Optional[License] = None,  # pylint: disable=redefined-builtin
        security: Optional[List[SecurityRequirement]] = None,
        servers: Optional[List[Server]] = None,
        summary: Optional[str] = None,
        tags: Optional[List[Tag]] = None,
        terms_of_service: Optional[AnyUrl] = None,
        webhooks: Optional[Dict[str, Union[PathItem, Reference]]] = None,
    ):
        if logging_config:
            logging_config.configure(debug)
        self._debug = debug
        self.state = State()
        self.router = RootRouter(
            route_handlers=route_handlers or [],
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            lifespan=lifespan,
            dependencies=dependencies,
            openapi_media_type=openapi_media_type,
            openapi_schema_url=openapi_schema_url,
            openapi_schema=OpenAPI(
                externalDocs=external_docs,
                security=security,
                servers=servers or [Server(url="/")],
                tags=tags,
                webhooks=webhooks,
                info=Info(
                    title=title,
                    version=version,
                    description=description,
                    contact=contact,
                    license=license,
                    summary=summary,
                    termsOfService=terms_of_service,
                ),
            ),
        )
        self.exception_handlers = dict(exception_handlers) if exception_handlers else {}
        self.user_middleware = list(middleware) if middleware else []
        self.middleware_stack = self.build_middleware_stack()

    def register(self, route_handler: Union[Type["Controller"], RouteHandler, Router, Callable]):
        """
        Proxy method for Route.register(**kwargs)
        """
        self.router.register(value=route_handler)

    # these Starlette properties are not supported
    route = DeprecatedProperty()
    add_route = DeprecatedProperty()
