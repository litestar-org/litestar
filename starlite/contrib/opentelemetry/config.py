from typing import Callable, List, Optional, Tuple, Type, Union

from pydantic import BaseConfig, BaseModel

from starlite.contrib.opentelemetry.middleware import (
    OpenTelemetryInstrumentationMiddleware,
)
from starlite.contrib.opentelemetry.utils import get_route_details_from_scope
from starlite.exceptions import MissingDependencyException
from starlite.middleware.base import DefineMiddleware
from starlite.types import Scope, Scopes

try:
    from opentelemetry.metrics import Meter, MeterProvider
    from opentelemetry.trace import Span, TracerProvider  # pyright: ignore
except ImportError as e:
    raise MissingDependencyException("OpenTelemetry dependencies are not installed") from e


OpenTelemetryHookHandler = Callable[[Span, dict], None]


class OpenTelemetryConfig(BaseModel):
    """Configuration class for the OpenTelemetry middleware.

    Consult the [OpenTelemetry ASGI documentation](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/asgi/asgi.html) for more info about the configuration options.
    """

    class Config(BaseConfig):
        arbitrary_types_allowed = True

    scope_span_details_extractor: Callable[[Scope], Tuple[str, dict]] = get_route_details_from_scope
    """Callback which should return a string and a tuple, representing the desired default span name and a dictionary
    with any additional span attributes to set.
    """
    server_request_hook_handler: Optional[OpenTelemetryHookHandler] = None
    """Optional callback which is called with the server span and ASGI scope object for every incoming request."""
    client_request_hook_handler: Optional[OpenTelemetryHookHandler] = None
    """Optional callback which is called with the internal span and an ASGI scope which is sent as a dictionary for when
    the method receive is called.
    """
    client_response_hook_handler: Optional[OpenTelemetryHookHandler] = None
    """Optional callback which is called with the internal span and an ASGI event which is sent as a dictionary for when
    the method send is called.
    """
    meter_provider: Optional[MeterProvider] = None
    """Optional meter provider to use.

    If omitted the current globally configured one is used.
    """
    tracer_provider: Optional[TracerProvider] = None
    """Optional tracer provider to use.

    If omitted the current globally configured one is used.
    """
    meter: Optional[Meter] = None
    """Optional meter to use.

    If omitted the provided meter provider or the global one will be used.
    """
    exclude: Optional[Union[str, List[str]]] = None
    """A pattern or list of patterns to skip in the Allowed Hosts middleware."""
    exclude_opt_key: Optional[str] = None
    """An identifier to use on routes to disable hosts check for a particular route."""
    exclude_urls_env_key: str = "STARLITE"
    """Key to use when checking whether a list of excluded urls is passed via ENV.

    OpenTelemetry supports excluding urls by passing an env in the format '{exclude_urls_env_key}_EXCLUDED_URLS'. With
    the default being 'STARLITE_EXCLUDED_URLS'.
    """
    scopes: Optional[Scopes] = None
    """ASGI scopes processed by the middleware, if None both 'http' and 'websocket' will be processed."""
    middleware_class: Type[OpenTelemetryInstrumentationMiddleware] = OpenTelemetryInstrumentationMiddleware
    """The middleware class to use.

    Should be a subclass of OpenTelemetry
    InstrumentationMiddleware][starlite.contrib.opentelemetry.OpenTelemetryInstrumentationMiddleware].
    """

    @property
    def middleware(self) -> DefineMiddleware:
        """Create an instance of [DefineMiddleware][starlite.middleware.base.DefineMiddleware] that wraps with.

        [OpenTelemetry
        InstrumentationMiddleware][starlite.contrib.opentelemetry.OpenTelemetryInstrumentationMiddleware] or a subclass
        of this middleware.

        Returns:
            An instance of `DefineMiddleware`.
        """
        return DefineMiddleware(self.middleware_class, config=self)
