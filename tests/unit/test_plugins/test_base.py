# pyright: reportUnnecessaryTypeIgnoreComment=false

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from advanced_alchemy.extensions.litestar import SQLAlchemySerializationPlugin
from click import Group

from litestar import Litestar, MediaType, get
from litestar.constants import UNDEFINED_SENTINELS
from litestar.file_system import FileSystemRegistry
from litestar.plugins import CLIPlugin, InitPlugin, OpenAPISchemaPlugin, OpenAPISpecPlugin, PluginRegistry
from litestar.plugins.attrs import AttrsSchemaPlugin
from litestar.plugins.core import MsgspecDIPlugin
from litestar.plugins.pydantic import PydanticDIPlugin, PydanticInitPlugin, PydanticPlugin, PydanticSchemaPlugin
from litestar.testing import create_test_client
from litestar.typing import FieldDefinition

if TYPE_CHECKING:
    from litestar.config.app import AppConfig


def test_plugin_on_app_init() -> None:
    @get("/", media_type=MediaType.TEXT)
    def greet() -> str:
        return "hello world"

    tag = "on_app_init_called"

    def on_startup(app: Litestar) -> None:
        app.state.called = True

    class PluginWithInitOnly(InitPlugin):
        def on_app_init(self, app_config: AppConfig) -> AppConfig:
            app_config.tags.append(tag)
            app_config.on_startup.append(on_startup)
            app_config.route_handlers.append(greet)
            return app_config

    with create_test_client(plugins=[PluginWithInitOnly()]) as client:
        response = client.get("/")
        assert response.text == "hello world"

        assert tag in client.app.tags
        assert client.app.state.called


def test_plugin_registry() -> None:
    class MyCLIPlugin(CLIPlugin):
        def on_cli_init(self, cli: Group) -> None:
            pass

    cli_plugin = MyCLIPlugin()
    serialization_plugin = SQLAlchemySerializationPlugin()
    openapi_plugin = PydanticSchemaPlugin()
    init_plugin = PydanticInitPlugin()

    registry = PluginRegistry([cli_plugin, serialization_plugin, openapi_plugin, init_plugin])

    assert registry.openapi == (openapi_plugin,)
    assert registry.cli == (cli_plugin,)
    assert registry.serialization == (serialization_plugin,)
    assert registry.init == (init_plugin,)

    assert openapi_plugin in registry
    assert serialization_plugin in registry
    assert init_plugin in registry
    assert cli_plugin in registry

    assert set(registry) == {openapi_plugin, cli_plugin, init_plugin, serialization_plugin}


def test_plugin_registry_get() -> None:
    class MyCLIPlugin(CLIPlugin):
        def on_cli_init(self, cli: Group) -> None:
            pass

    cli_plugin = MyCLIPlugin()

    with pytest.raises(KeyError, match="No plugin of type 'MyCLIPlugin' registered"):
        PluginRegistry([]).get(MyCLIPlugin)

    assert PluginRegistry([cli_plugin]).get(MyCLIPlugin) is cli_plugin


def test_plugin_registry_stringified_get() -> None:
    class MyCLIPlugin(CLIPlugin):
        def on_cli_init(self, cli: Group) -> None:
            pass

    cli_plugin = MyCLIPlugin()
    pydantic_plugin = PydanticPlugin()
    with pytest.raises(KeyError):
        PluginRegistry([MyCLIPlugin()]).get(
            "litestar2.plugins.pydantic.PydanticPlugin"
        )  # not a fqdn.  should fail # type: ignore[list-item]
        PluginRegistry([]).get("CLIPlugin")  # not a fqdn.  should fail # type: ignore[list-item]

    assert PluginRegistry([cli_plugin, pydantic_plugin]).get(MyCLIPlugin) is cli_plugin
    assert PluginRegistry([cli_plugin, pydantic_plugin]).get(PydanticPlugin) is pydantic_plugin
    assert PluginRegistry([cli_plugin, pydantic_plugin]).get("PydanticPlugin") is pydantic_plugin
    assert (
        PluginRegistry([cli_plugin, pydantic_plugin]).get("litestar.plugins.pydantic.PydanticPlugin") is pydantic_plugin
    )


def test_openapi_schema_plugin_is_constrained_field() -> None:
    assert OpenAPISchemaPlugin.is_constrained_field(FieldDefinition.from_annotation(str)) is False


def test_openapi_schema_plugin_is_undefined_sentinel() -> None:
    for value in UNDEFINED_SENTINELS:
        assert OpenAPISchemaPlugin.is_undefined_sentinel(value) is False


def test_openapi_spec_plugin_in_public_namespaces() -> None:
    """``OpenAPISpecPlugin`` is exported from both ``litestar.plugins`` and ``litestar.plugins.base``."""
    import litestar.plugins as plugins_pkg
    import litestar.plugins.base as plugins_base

    assert "OpenAPISpecPlugin" in plugins_pkg.__all__
    assert "OpenAPISpecPlugin" in plugins_base.__all__
    assert plugins_pkg.OpenAPISpecPlugin is plugins_base.OpenAPISpecPlugin


def test_openapi_spec_plugin_slots_are_minimal() -> None:
    """``__slots__`` only declares the include/exclude filter attributes — no instance dict."""
    assert OpenAPISpecPlugin.__slots__ == ("exclude", "include")
    # Subclasses without __dict__ cannot grow ad-hoc attributes.
    plugin = OpenAPISpecPlugin()
    with pytest.raises(AttributeError):
        plugin.foo = 1  # type: ignore[attr-defined]


def test_openapi_spec_plugin_default_methods_return_none() -> None:
    """A bare subclass returns ``None`` from both default contribution methods."""

    class Bare(OpenAPISpecPlugin):
        pass

    plugin = Bare()
    assert plugin.get_openapi_components() is None
    # The default ``get_openapi_security_requirements`` ignores its argument; pass ``None``.
    assert plugin.get_openapi_security_requirements(None) is None  # type: ignore[arg-type]


def test_openapi_spec_plugin_subclass_isinstance() -> None:
    """Subclasses are detectable via ``isinstance`` so the registry can collect them."""

    class Concrete(OpenAPISpecPlugin):
        pass

    assert isinstance(Concrete(), OpenAPISpecPlugin)


def test_plugin_registry_openapi_spec_collected() -> None:
    """Registering an ``OpenAPISpecPlugin`` instance exposes it via the registry."""

    class MySpecPlugin(OpenAPISpecPlugin):
        pass

    spec_plugin = MySpecPlugin()
    schema_plugin = PydanticSchemaPlugin()

    registry = PluginRegistry([spec_plugin, schema_plugin])

    assert registry.openapi_spec == (spec_plugin,)
    # Schema plugins remain collected separately and are not aliased into the new collection.
    assert registry.openapi == (schema_plugin,)


def test_plugin_registry_openapi_spec_preserves_registration_order() -> None:
    """Registration order is preserved across multiple ``OpenAPISpecPlugin`` instances."""

    class A(OpenAPISpecPlugin):
        pass

    class B(OpenAPISpecPlugin):
        pass

    class C(OpenAPISpecPlugin):
        pass

    a, b, c = A(), B(), C()
    registry = PluginRegistry([a, b, c])

    assert registry.openapi_spec == (a, b, c)


def test_plugin_registry_openapi_spec_excludes_non_spec_plugins() -> None:
    """Non-``OpenAPISpecPlugin`` instances are not collected into ``openapi_spec``."""

    class MyCLIPlugin(CLIPlugin):
        def on_cli_init(self, cli: Group) -> None:
            pass

    registry = PluginRegistry([MyCLIPlugin(), PydanticSchemaPlugin(), PydanticInitPlugin()])

    assert registry.openapi_spec == ()


@pytest.mark.parametrize(("init_plugin",), [(PydanticInitPlugin(),), (None,)])
@pytest.mark.parametrize(("schema_plugin",), [(PydanticSchemaPlugin(),), (None,)])
@pytest.mark.parametrize(("attrs_plugin",), [(AttrsSchemaPlugin(),), (None,)])
def test_app_get_default_plugins(
    init_plugin: PydanticInitPlugin, schema_plugin: PydanticSchemaPlugin, attrs_plugin: AttrsSchemaPlugin
) -> None:
    plugins = [p for p in (init_plugin, schema_plugin, attrs_plugin) if p is not None]
    any_pydantic = bool(init_plugin) or bool(schema_plugin)
    default_plugins = Litestar._get_default_plugins(plugins)  # type: ignore[arg-type]
    if not any_pydantic:
        assert {type(p) for p in default_plugins} == {
            PydanticPlugin,
            AttrsSchemaPlugin,
            PydanticDIPlugin,
            MsgspecDIPlugin,
            FileSystemRegistry,
        }
    else:
        assert {type(p) for p in default_plugins} == {
            PydanticInitPlugin,
            PydanticSchemaPlugin,
            AttrsSchemaPlugin,
            PydanticDIPlugin,
            MsgspecDIPlugin,
            FileSystemRegistry,
        }
