from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any, cast

from litestar.handlers.base import BaseRouteHandler
from litestar.middleware.base import DefineMiddleware
from litestar.plugins import InitPlugin
from litestar.plugins.opentelemetry.config import OpenTelemetryConfig
from litestar.plugins.opentelemetry.instrumentation import (
    _is_otel_available,
    create_span,
    create_span_async,
    instrument_lifecycle_event,
)
from litestar.plugins.opentelemetry.middleware import OpenTelemetryInstrumentationMiddleware

if TYPE_CHECKING:
    from litestar.config.app import AppConfig
    from litestar.connection import ASGIConnection
    from litestar.types import Scope
    from litestar.types.composite_types import Middleware

_GUARDS_PATCHED = False
_EVENTS_PATCHED = False
_CLI_PATCHED = False


class OpenTelemetryPlugin(InitPlugin):
    """OpenTelemetry Plugin."""

    __slots__ = ("_middleware", "config")

    def __init__(self, config: OpenTelemetryConfig | None = None) -> None:
        self.config = config or OpenTelemetryConfig()
        self._middleware: DefineMiddleware | None = None
        super().__init__()

    @property
    def middleware(self) -> DefineMiddleware:
        if self._middleware:
            return self._middleware
        return DefineMiddleware(OpenTelemetryInstrumentationMiddleware, config=self.config)

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        app_config.middleware, existing_middleware = self._pop_otel_middleware(app_config.middleware)

        middleware_to_use = existing_middleware or self.middleware
        app_config.middleware.insert(0, middleware_to_use)

        if self.config.instrument_guards:
            self._instrument_guards()

        if self.config.instrument_events:
            self._instrument_events()

        if self.config.instrument_lifecycle:
            self._instrument_lifecycle(app_config)

        if self.config.instrument_cli:
            self._instrument_cli()

        if self.config.tracer_provider is not None:
            # Ensure the configured tracer provider is active so helper instrumentation uses the same provider. If a
            # provider is already set, mirror the span processors onto it to avoid the OTEL override warning.
            from opentelemetry import trace

            current_provider = trace.get_tracer_provider()
            if current_provider is self.config.tracer_provider:
                trace.set_tracer_provider(self.config.tracer_provider)
            else:
                configured_processors = getattr(
                    getattr(self.config.tracer_provider, "_active_span_processor", None), "_span_processors", None
                )
                target_provider = getattr(current_provider, "_tracer_provider", current_provider)
                if configured_processors:
                    for processor in configured_processors:
                        if hasattr(target_provider, "add_span_processor"):
                            target_provider.add_span_processor(processor)  # pyright: ignore[reportAttributeAccessIssue]
                        else:  # Fallback when provider cannot be mutated
                            trace.set_tracer_provider(self.config.tracer_provider)
                            break
                else:
                    # As a last resort, force the configured provider to be used so its span processors are honored.
                    trace._TRACER_PROVIDER = self.config.tracer_provider

            from litestar.plugins.opentelemetry import instrumentation as otel_instrumentation

            otel_instrumentation._CUSTOM_TRACER_PROVIDER = self.config.tracer_provider

        app_config.after_exception.append(self._record_exception)

        return app_config

    async def _record_exception(self, exc: Exception, scope: Scope) -> None:
        """Record exceptions on the active span if available.

        This hook is registered as an ``after_exception`` handler to ensure span recording even when middleware order
        places the OpenTelemetry middleware inside the exception handling middleware.
        """

        from opentelemetry import trace
        from opentelemetry.trace import Status, StatusCode

        span = trace.get_current_span()
        if span.get_span_context().is_valid and span.is_recording():
            import traceback

            span.record_exception(
                exc,
                attributes={
                    "exception.stacktrace": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
                },
            )
            span.set_status(Status(StatusCode.ERROR, str(exc)))

    def _instrument_guards(self) -> None:
        global _GUARDS_PATCHED
        if _GUARDS_PATCHED:
            return

        original_authorize = BaseRouteHandler.authorize_connection

        async def authorize_with_spans(self: BaseRouteHandler, connection: ASGIConnection[Any, Any, Any, Any]) -> None:
            if not _is_otel_available() or not self.guards:
                return await original_authorize(self, connection)

            scope: dict[str, Any] = (
                cast("dict[str, Any]", connection.scope) if isinstance(getattr(connection, "scope", None), dict) else {}
            )
            conn_type = scope.get("type", "unknown")

            for guard in self.guards:
                guard_name = getattr(guard, "__name__", str(guard))
                handler_name = getattr(self, "handler_name", str(self))

                async with create_span_async(
                    f"guard.{guard_name}",
                    attributes={
                        "litestar.guard.name": guard_name,
                        "litestar.handler.name": handler_name,
                        "litestar.connection.type": conn_type,
                    },
                ):
                    await guard(connection, self)
            return None

        setattr(BaseRouteHandler, "authorize_connection", cast("Any", authorize_with_spans))
        _GUARDS_PATCHED = True

    def _instrument_events(self) -> None:
        try:
            from litestar.events.emitter import SimpleEventEmitter
        except ImportError:  # pragma: no cover - emitter may be absent
            return

        global _EVENTS_PATCHED
        if _EVENTS_PATCHED:
            return

        original_emit = SimpleEventEmitter.emit

        def emit_with_span(self: SimpleEventEmitter, event_id: str, *args: Any, **kwargs: Any) -> None:
            if not _is_otel_available():
                return original_emit(self, event_id, *args, **kwargs)

            def make_wrapped(listener_name: str, event_id: str, fn: Any) -> Any:
                """Create a wrapped listener function with properly bound loop variables."""

                async def wrapped(*a: Any, **kw: Any) -> None:
                    async with create_span_async(
                        f"event.listener.{listener_name}",
                        attributes={
                            "litestar.event.listener": listener_name,
                            "litestar.event.id": event_id,
                        },
                    ):
                        result = fn(*a, **kw)
                        if inspect.isawaitable(result):
                            await result

                return wrapped

            if listeners := self.listeners.get(event_id):
                with create_span(f"event.emit.{event_id}", attributes={"litestar.event.id": event_id}):
                    for listener in listeners:
                        fn = listener.fn
                        listener_name = getattr(fn, "__name__", str(fn))
                        wrapped = make_wrapped(listener_name, event_id, fn)

                        if self._send_stream is not None:
                            self._send_stream.send_nowait((wrapped, args, kwargs))
                return None

            return original_emit(self, event_id, *args, **kwargs)

        setattr(SimpleEventEmitter, "emit", cast("Any", emit_with_span))
        _EVENTS_PATCHED = True

    def _instrument_lifecycle(self, app_config: AppConfig) -> None:
        if not _is_otel_available():
            return

        app_config.on_startup = [instrument_lifecycle_event("startup")(fn) for fn in app_config.on_startup]
        app_config.on_shutdown = [instrument_lifecycle_event("shutdown")(fn) for fn in app_config.on_shutdown]

    def _instrument_cli(self) -> None:
        if not _is_otel_available():
            return

        try:
            import click

            from litestar.cli.main import litestar_group
        except ImportError:  # pragma: no cover - CLI not available in some contexts
            return

        global _CLI_PATCHED
        if _CLI_PATCHED:
            return

        original_command_invoke = click.Command.invoke
        original_group_invoke = getattr(click.Group, "invoke", None)

        def _span_attrs(ctx: click.Context) -> dict[str, Any]:
            return {
                "litestar.cli.command": ctx.command_path or ctx.command.name or "cli",
                "litestar.cli.params": sorted(ctx.params.keys()),
                "litestar.cli.obj_present": ctx.obj is not None,
            }

        def invoke_with_span(command: click.Command, ctx: click.Context) -> Any:
            with create_span(f"cli.{ctx.command_path or command.name or 'cli'}", attributes=_span_attrs(ctx)):
                return original_command_invoke(command, ctx)

        def group_invoke_with_span(command: click.Group, ctx: click.Context) -> Any:
            with create_span(f"cli.{ctx.command_path or command.name or 'cli'}", attributes=_span_attrs(ctx)):
                if original_group_invoke:
                    return original_group_invoke(command, ctx)
                return original_command_invoke(command, ctx)

        setattr(click.Command, "invoke", cast("Any", invoke_with_span))
        setattr(click.Group, "invoke", cast("Any", group_invoke_with_span))
        _CLI_PATCHED = True

        _ = litestar_group

    @staticmethod
    def _pop_otel_middleware(middlewares: list[Middleware]) -> tuple[list[Middleware], DefineMiddleware | None]:
        """Get the OpenTelemetry middleware if it is enabled in the application.
        Remove the middleware from the list of middlewares if it is found.
        """
        otel_middleware: DefineMiddleware | None = None
        other_middlewares = []
        for middleware in middlewares:
            if (
                isinstance(middleware, DefineMiddleware)
                and isinstance(middleware.middleware, type)
                and issubclass(middleware.middleware, OpenTelemetryInstrumentationMiddleware)
            ):
                otel_middleware = middleware
            else:
                other_middlewares.append(middleware)
        return other_middlewares, otel_middleware
