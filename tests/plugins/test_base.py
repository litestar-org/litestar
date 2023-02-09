from typing import TYPE_CHECKING, Any, Dict, Type

import pytest
from pydantic import BaseModel

from starlite import MediaType, Starlite, State, get
from starlite.plugins.base import (
    InitPluginProtocol,
    PluginMapping,
    SerializationPluginProtocol,
)
from starlite.testing import create_test_client

if TYPE_CHECKING:
    from typing_extensions import TypeGuard


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
    def to_data_container_class(self, model_class: Type[AModel], **kwargs: Any) -> Type[BaseModel]:
        assert model_class is AModel
        return APydanticModel

    @staticmethod
    def is_plugin_supported_type(value: Any) -> "TypeGuard[AModel]":
        return value is AModel

    def from_data_container_instance(self, model_class: Type[AModel], data_container_instance: BaseModel) -> AModel:
        assert model_class is AModel
        assert isinstance(data_container_instance, APydanticModel)
        return model_class(**data_container_instance.dict())

    def to_dict(self, model_instance: AModel) -> Dict[str, Any]:
        return dict(model_instance)  # type: ignore

    def from_dict(self, model_class: Type[AModel], **kwargs: Any) -> AModel:
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
        def on_app_init(self, app: "Starlite") -> None:
            app.tags.append(tag)
            app.on_startup.append(on_startup)
            app.register(greet)

    with create_test_client(plugins=[PluginWithInitOnly()]) as client:
        response = client.get("/")
        assert response.text == "hello world"

        assert tag in client.app.tags
        assert client.app.state.called
