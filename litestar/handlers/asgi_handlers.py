from collections.abc import Callable, Mapping, Sequence
from typing import Any

from litestar.connection import ASGIConnection
from litestar.exceptions import ImproperlyConfiguredException
from litestar.handlers.base import BaseRouteHandler
from litestar.router import Router
from litestar.types import (
    AsyncAnyCallable,
    ExceptionHandlersMap,
    Guard,
    ParametersMap,
)
from litestar.types.builtin_types import NoneType
from litestar.utils.predicates import is_async_callable

__all__ = ("ASGIRouteHandler", "asgi")


class ASGIRouteHandler(BaseRouteHandler):
    __slots__ = (
        "_lifespan_state",
        "copy_scope",
        "copy_state",
        "is_mount",
        "lifespan",
    )

    def __init__(
        self,
        path: str | Sequence[str] | None = None,
        *,
        fn: AsyncAnyCallable,
        exception_handlers: ExceptionHandlersMap | None = None,
        guards: Sequence[Guard] | None = None,
        name: str | None = None,
        opt: Mapping[str, Any] | None = None,
        is_mount: bool = False,
        signature_namespace: Mapping[str, Any] | None = None,
        copy_scope: bool = True,
        parameters: ParametersMap | None = None,
        lifespan: bool = False,
        copy_state: bool = False,
        **kwargs: Any,
    ) -> None:
        """Route handler for ASGI routes.

        Args:
            path: A path fragment for the route handler function or a list of path fragments. If not given defaults to
                ``/``.
            fn: The handler function.

                .. versionadded:: 3.0
            exception_handlers: A mapping of status codes and/or exception types to handler functions.
            guards: A sequence of :class:`Guard <.types.Guard>` callables.
            name: A string identifying the route handler.
            opt: A string key mapping of arbitrary values that can be accessed in :class:`Guards <.types.Guard>` or
                wherever you have access to :class:`Request <.connection.Request>` or
                :class:`ASGI Scope <.types.Scope>`.
            is_mount: A boolean dictating whether the handler's paths should be regarded as mount paths. A mount path
                accepts its own path and any sub path under it. For example, a mount with the path ``/some-path/``
                will accept requests for ``/some-path/`` and any sub path under this, e.g. ``/some-path/sub-path/``
                etc., but not ``/some-path-other/``.
            signature_namespace: A mapping of names to types for use in forward reference resolution during signature modelling.
            type_encoders: A mapping of types to callables that transform them into types supported for serialization.
            copy_scope: Copy the ASGI 'scope' before calling the wrapped ASGI application. The copy is shallow, so
                nested values such as 'scope["state"]' remain shared, unless 'copy_state' is set. Set to 'False' if
                the wrapped application is meant to communicate with the outer application through the scope
            parameters: A mapping of :func:`Parameter <.params.ParameterKwarg>` definitions
            lifespan: Run the ASGI lifespan of the wrapped ASGI application during the lifespan of the Litestar
                application the handler is registered on
            copy_state: Copy 'scope["state"]' before calling the wrapped ASGI application. The copy is shallow.
                Requires 'copy_scope'
            **kwargs: Any additional kwarg - will be set in the opt dictionary.

        Raises:
            ImproperlyConfiguredException: If ``copy_state`` is set and ``copy_scope`` is not.
        """
        if copy_state and not copy_scope:
            raise ImproperlyConfiguredException("'copy_state=True' requires 'copy_scope=True'")

        self.is_mount = is_mount
        self.copy_scope = copy_scope
        self.copy_state = copy_state
        self.lifespan = lifespan
        self._lifespan_state: dict[str, Any] = {}

        super().__init__(
            path,
            fn=fn,
            exception_handlers=exception_handlers,
            guards=guards,
            name=name,
            opt=opt,
            signature_namespace=signature_namespace,
            parameters=parameters,
            **kwargs,
        )

    def _get_merge_opts(self, others: tuple[Router, ...]) -> dict[str, Any]:
        merge_opts = super()._get_merge_opts(others)
        merge_opts["is_mount"] = self.is_mount
        merge_opts["copy_scope"] = self.copy_scope
        merge_opts["copy_state"] = self.copy_state
        merge_opts["lifespan"] = self.lifespan
        return merge_opts

    def _validate_handler_function(self) -> None:
        """Validate the route handler function once it's set by inspecting its return annotations."""
        super()._validate_handler_function()

        if not self.parsed_fn_signature.return_type.is_subclass_of(NoneType):
            raise ImproperlyConfiguredException("ASGI handler functions should return 'None'")

        if any(key not in self.parsed_fn_signature.parameters for key in ("scope", "send", "receive")):
            raise ImproperlyConfiguredException(
                "ASGI handler functions should define 'scope', 'send' and 'receive' arguments"
            )
        if not is_async_callable(self.fn):
            raise ImproperlyConfiguredException("Functions decorated with 'asgi' must be async functions")

    async def handle(self, connection: ASGIConnection["ASGIRouteHandler", Any, Any, Any]) -> None:
        """ASGI app that authorizes the connection and then awaits the handler function.

        .. versionadded: 3.0

        Args:
                connection: The ASGI connection

        Returns:
                None
        """

        if self.guards:
            await self.authorize_connection(connection=connection)

        if self._lifespan_state:
            connection.scope["state"].update(self._lifespan_state)

        await self.fn(scope=connection.scope, receive=connection.receive, send=connection.send)


def asgi(
    path: str | Sequence[str] | None = None,
    *,
    exception_handlers: ExceptionHandlersMap | None = None,
    guards: Sequence[Guard] | None = None,
    name: str | None = None,
    opt: Mapping[str, Any] | None = None,
    is_mount: bool = False,
    signature_namespace: Mapping[str, Any] | None = None,
    copy_scope: bool = True,
    handler_class: type[ASGIRouteHandler] = ASGIRouteHandler,
    lifespan: bool = False,
    copy_state: bool = False,
    **kwargs: Any,
) -> Callable[[AsyncAnyCallable], ASGIRouteHandler]:
    """Create an :class:`ASGIRouteHandler`.

    Args:
        path: A path fragment for the route handler function or a sequence of path fragments. If not given defaults
            to ``/``
        exception_handlers: A mapping of status codes and/or exception types to handler functions.
        guards: A sequence of :class:`Guard <.types.Guard>` callables.
        name: A string identifying the route handler.
        opt: A string keyed mapping of arbitrary values that can be accessed in :class:`Guards <.types.Guard>` or
            wherever you have access to :class:`Request <.connection.Request>` or
            :class:`ASGI Scope <.types.Scope>`.
        signature_namespace: A mapping of names to types for use in forward reference resolution during signature
            modelling.
        is_mount: A boolean dictating whether the handler's paths should be regarded as mount paths. A mount path
            accepts its own path and any sub path under it. For example, a mount with the path ``/some-path/`` will
            accept requests for ``/some-path/`` and any sub path under this, e.g. ``/some-path/sub-path/`` etc., but
            not ``/some-path-other/``.
        copy_scope: Copy the ASGI 'scope' before calling the wrapped ASGI application. The copy is shallow, so
            nested values such as 'scope["state"]' remain shared, unless 'copy_state' is set. Set to 'False' if the
            wrapped application is meant to communicate with the outer application through the scope
        handler_class: Route handler class instantiated by the decorator
        lifespan: Run the ASGI lifespan of the wrapped ASGI application during the lifespan of the Litestar
            application the handler is registered on
        copy_state: Copy 'scope["state"]' before calling the wrapped ASGI application. The copy is shallow.
            Requires 'copy_scope'
        **kwargs: Any additional kwarg - will be set in the opt dictionary.
    """

    def decorator(fn: AsyncAnyCallable) -> ASGIRouteHandler:
        return handler_class(
            fn=fn,
            path=path,
            exception_handlers=exception_handlers,
            guards=guards,
            name=name,
            opt=opt,
            is_mount=is_mount,
            signature_namespace=signature_namespace,
            copy_scope=copy_scope,
            lifespan=lifespan,
            copy_state=copy_state,
            **kwargs,
        )

    return decorator
