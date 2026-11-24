from litestar import Router, WebSocket, get, post, websocket
from litestar.dto._plan import handler_name_scope
from litestar.dto._registry import TransferModelNaming, TransferModelRegistry


def fetch() -> None:
    return None


@get("/x")
async def handler() -> None:
    return None


def test_name_for_returns_preferred_when_free() -> None:
    assert TransferModelRegistry().name_for("k", "A", "m.A") == "A"


def test_name_for_falls_back_to_qualified_then_numbered() -> None:
    registry = TransferModelRegistry()

    assert [registry.name_for(key, "A", "m.A") for key in ("k1", "k2", "k3", "k4")] == ["A", "m.A", "m.A_0", "m.A_1"]


def test_name_for_is_idempotent_per_key() -> None:
    registry = TransferModelRegistry()

    first = registry.name_for("k", "A", "m.A")
    repeated = registry.name_for("k", "B", "m.B")

    assert (first, repeated) == ("A", "A")
    assert registry.name_for("other", "A", "m.A") == "m.A"


def test_registries_are_independent() -> None:
    assert TransferModelRegistry().name_for("k", "A", "m.A") == TransferModelRegistry().name_for("k", "A", "m.A") == "A"


def test_naming_numbers_repeats_of_one_model_name() -> None:
    naming = TransferModelNaming(TransferModelRegistry(), "scope")

    names = [naming.name_for(is_data_field=False, model_name="PostUser", preferred="A", qualified="m.A") for _ in "abc"]

    assert names == ["A", "m.A", "m.A_0"]


def test_naming_with_same_scope_reuses_names() -> None:
    registry = TransferModelRegistry()

    def three_names(naming: TransferModelNaming) -> list[str]:
        return [
            naming.name_for(is_data_field=False, model_name="PostUser", preferred="A", qualified="m.A") for _ in "abc"
        ]

    first = three_names(TransferModelNaming(registry, "scope"))
    second = three_names(TransferModelNaming(registry, "scope"))
    other = TransferModelNaming(registry, "other").name_for(
        is_data_field=False, model_name="PostUser", preferred="A", qualified="m.A"
    )

    assert first == second == ["A", "m.A", "m.A_0"]
    assert other == "m.A_1"


def test_naming_counts_ordinals_across_directions() -> None:
    registry = TransferModelRegistry()

    def both_directions(naming: TransferModelNaming) -> list[str]:
        return [
            naming.name_for(is_data_field=True, model_name="PostUser", preferred="Req", qualified="m.Req"),
            naming.name_for(is_data_field=False, model_name="PostUser", preferred="Resp", qualified="m.Resp"),
        ]

    assert both_directions(TransferModelNaming(registry, "scope")) == ["Req", "Resp"]
    assert both_directions(TransferModelNaming(registry, "scope")) == ["Req", "Resp"]


def test_handler_name_scope_survives_merge() -> None:
    router = Router("/r", route_handlers=[handler])

    first = handler.merge(router)
    second = handler.merge(router)

    assert first is not second
    assert handler_name_scope(first) == handler_name_scope(second)


def test_handler_name_scope_separates_one_handler_under_two_routers() -> None:
    first = handler.merge(Router("/r1", route_handlers=[handler]))
    second = handler.merge(Router("/r2", route_handlers=[handler]))

    assert handler_name_scope(first) != handler_name_scope(second)


def test_handler_name_scope_separates_http_methods() -> None:
    assert handler_name_scope(get("/s")(fetch)) != handler_name_scope(post("/s")(fetch))


def test_handler_name_scope_for_websocket_handler() -> None:
    @websocket("/ws")
    async def socket_handler(socket: WebSocket) -> None:
        return None

    scope = handler_name_scope(socket_handler)

    assert isinstance(scope, tuple)
    assert hash(scope) == hash(handler_name_scope(socket_handler))
    assert scope[3] == ()
