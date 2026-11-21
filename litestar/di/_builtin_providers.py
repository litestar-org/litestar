# pyright: reportUnnecessaryTypeIgnoreComment=false
from __future__ import annotations

from litestar._request_parameters.extraction import check_query_content_type
from litestar.app import Litestar
from litestar.connection import ASGIConnection, Request
from litestar.datastructures import Headers, ImmutableState, State
from litestar.di.provider import Provider, TypeDependency
from litestar.params import QueryParams, RawBody, RequestCookies
from litestar.types import Scope

__all__ = ("BuiltinProviderFactory",)


def _provide_headers(connection: ASGIConnection) -> Headers:
    return connection.headers


def _provide_query_params(connection: ASGIConnection) -> QueryParams:
    return QueryParams(connection.query_params)


def _provide_cookies(connection: ASGIConnection) -> RequestCookies:
    return RequestCookies(connection.cookies)


def _provide_scope(connection: ASGIConnection) -> Scope:
    return connection.scope


async def _provide_raw_body(request: Request) -> RawBody:
    check_query_content_type(request)
    return RawBody(await request.body())


def _provide_state(app: TypeDependency[Litestar]) -> State:
    return app.state


class BuiltinProviderFactory:
    """Create the seeds and providers of the values Litestar supplies to an app's registries, each
    once per app
    """

    __slots__ = ("_connection_seeds", "_raw_body_provider", "_request_value_providers", "_state_providers", "app_seeds")

    def __init__(self, app: Litestar) -> None:
        """Create a factory for the registries of ``app``.

        Args:
            app: The app
        """
        self.app_seeds: tuple[Provider, ...] = (
            (Provider.seed(Litestar, scope="app"),)
            if type(app) is Litestar
            else (Provider.seed(Litestar, scope="app"), Provider.seed(type(app), scope="app"))
        )
        """The seeds of the app, with scope ``"app"``: one under :class:`~litestar.app.Litestar`,
        and one under the app's class if it is a subclass
        """
        self._request_value_providers = (
            Provider(_provide_headers, key=Headers, scope="handler", sync_to_thread=False),
            Provider(_provide_query_params, key=QueryParams, scope="handler", sync_to_thread=False),  # pyright: ignore[reportArgumentType]
            Provider(_provide_cookies, key=RequestCookies, scope="handler", sync_to_thread=False),  # pyright: ignore[reportArgumentType]
            Provider(_provide_scope, key=Scope, scope="handler", sync_to_thread=False),  # type: ignore[arg-type]
        )
        self._raw_body_provider = Provider(_provide_raw_body, key=RawBody, scope="handler")  # pyright: ignore[reportArgumentType]
        self._connection_seeds: dict[type[ASGIConnection], Provider] = {}
        self._state_providers: dict[type[ImmutableState], Provider] = {
            State: Provider(_provide_state, key=State, scope="app", sync_to_thread=False)
        }

    def connection_seeds(self, connection_class: type[ASGIConnection]) -> tuple[Provider, ...]:
        """Return the seeds of a connection, with scope ``"handler"``: one under
        ``connection_class`` and one under each class it inherits from up to
        :class:`~litestar.connection.ASGIConnection`. The same objects for every call
        """
        seeds = []
        for cls in connection_class.__mro__:
            if not issubclass(cls, ASGIConnection):
                continue
            if (seed := self._connection_seeds.get(cls)) is None:
                seed = self._connection_seeds[cls] = Provider.seed(cls, scope="handler")
            seeds.append(seed)
        return tuple(seeds)

    def request_value_providers(self, *, accepts_body: bool) -> tuple[Provider, ...]:
        """Return the providers of :class:`~litestar.datastructures.Headers`,
        :data:`~litestar.params.QueryParams`, :data:`~litestar.params.RequestCookies` and
        :data:`~litestar.types.Scope`, and with ``accepts_body`` of
        :data:`~litestar.params.RawBody`, each with scope ``"handler"``
        """
        if accepts_body:
            return (*self._request_value_providers, self._raw_body_provider)
        return self._request_value_providers

    def state_provider(self, state_class: type[ImmutableState]) -> Provider:
        """Return the provider of ``state_class``: for :class:`~litestar.datastructures.State` the
        app's state, and for a subclass of it a ``state_class`` built from the app's state, both
        with scope ``"app"``; for any other class a ``state_class`` built from the app's state,
        with scope ``"request"``. The same object for every call
        """
        if (provider := self._state_providers.get(state_class)) is None:

            def provide_state_class(app: TypeDependency[Litestar]) -> ImmutableState:
                return state_class(app.state)

            provider = self._state_providers[state_class] = Provider(
                provide_state_class,
                key=state_class,
                scope="app" if issubclass(state_class, State) else "request",
                sync_to_thread=False,
            )
        return provider
