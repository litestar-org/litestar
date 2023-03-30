from __future__ import annotations

from typing import TYPE_CHECKING, Any, List
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel
from typing_extensions import get_origin

from starlite import MediaType, get
from starlite.connection import Request
from starlite.plugins import (
    InitPluginProtocol,
    PluginMapping,
    SerializationPluginProtocol,
    get_plugin_for_value,
)
from starlite.testing import create_test_client

if TYPE_CHECKING:
    from typing_extensions import TypeGuard

    from starlite.config.app import AppConfig
    from starlite.datastructures import State


class AModel:
    def __init__(self, name: str) -> None:
        self.name = name

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, type(self)):
            return __o.name == self.name
        return False


class APydanticModel(BaseModel):
    name: str


class APlugin(SerializationPluginProtocol[AModel, BaseModel]):
    def to_data_container_class(self, model_class: type[AModel], **kwargs: Any) -> type[BaseModel]:
        assert model_class is AModel
        return APydanticModel

    @staticmethod
    def is_plugin_supported_type(value: Any) -> "TypeGuard[AModel]":
        return value is AModel

    def from_data_container_instance(self, model_class: type[AModel], data_container_instance: BaseModel) -> AModel:
        assert model_class is AModel
        assert isinstance(data_container_instance, APydanticModel)
        return model_class(**data_container_instance.dict())

    def to_dict(self, model_instance: AModel) -> dict[str, Any]:
        return dict(model_instance)  # type: ignore

    def from_dict(self, model_class: type[AModel], **kwargs: Any) -> AModel:
        assert model_class is AModel
        return model_class(**kwargs)


@pytest.mark.parametrize(
    ["input_value", "output_value"],
    [
        [APydanticModel(name="my name"), AModel(name="my name")],
        [[APydanticModel(name="1"), APydanticModel(name="2")], [AModel(name="1"), AModel(name="2")]],
        [(APydanticModel(name="1"), APydanticModel(name="2")), [AModel(name="1"), AModel(name="2")]],
    ],
)
def test_plugin_mapping_value_to_model_instance(input_value: Any, output_value: Any) -> None:
    mapping = PluginMapping(plugin=APlugin(), model_class=AModel)
    assert mapping.get_model_instance_for_value(input_value) == output_value


@get("/", media_type=MediaType.TEXT)
def greet() -> str:
    return "hello world"


def test_plugin_on_app_init() -> None:
    tag = "on_app_init_called"

    def on_startup(state: State) -> None:
        state.called = True

    class PluginWithInitOnly(InitPluginProtocol):
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


@pytest.mark.parametrize(("value", "tested_type"), [(List[int], int), (Request[Any, Any, Any], Request)])
def test_get_plugin_for_value(value: Any, tested_type: Any) -> None:
    mock_plugin = MagicMock(spec=SerializationPluginProtocol)
    mock_plugin.is_plugin_supported_type.return_value = False
    get_plugin_for_value(value, [mock_plugin])
    assert mock_plugin.is_plugin_supported_type.called_once()
    call = mock_plugin.is_plugin_supported_type.mock_calls[0]
    assert len(call.args) == 1
    assert get_origin(call.args[0]) or call.args[0] is tested_type
