from dataclasses import dataclass
from typing import Any, Dict, Type

import pytest
from pydantic import BaseModel

from starlite.plugins.base import ModelT, PluginMapping, PluginProtocol


class DummyPlugin(PluginProtocol[ModelT]):
    def to_pydantic_model_class(self, model_class: Type[ModelT], **kwargs: Any) -> Type[BaseModel]:
        raise NotImplementedError

    @staticmethod
    def is_plugin_supported_type(value: Any) -> bool:
        raise NotImplementedError

    def from_pydantic_model_instance(self, model_class: Type[ModelT], pydantic_model_instance: BaseModel) -> ModelT:
        raise NotImplementedError

    def to_dict(self, model_instance: ModelT) -> Dict[str, Any]:
        raise NotImplementedError

    def from_dict(self, model_class: Type[ModelT], **kwargs: Any) -> ModelT:
        raise NotImplementedError


@dataclass
class AModel:
    name: str


class APydanticModel(BaseModel):
    name: str


@pytest.mark.parametrize(
    ["input", "output"],
    [
        [APydanticModel(name="my name"), AModel(name="my name")],
        [[APydanticModel(name="1"), APydanticModel(name="2")], [AModel(name="1"), AModel(name="2")]],
        [(APydanticModel(name="1"), APydanticModel(name="2")), [AModel(name="1"), AModel(name="2")]],
    ],
)
def test_plugin_mapping_get_value_converted_to_model_class(input: Any, output: Any) -> None:
    class APlugin(DummyPlugin[AModel]):
        def from_pydantic_model_instance(self, model_class: Type[AModel], pydantic_model_instance: BaseModel) -> AModel:
            assert model_class is AModel
            assert isinstance(pydantic_model_instance, APydanticModel)
            return model_class(name=pydantic_model_instance.name)

    mapping = PluginMapping(plugin=APlugin(), model_class=AModel)
    assert mapping.get_value_converted_to_model_class(input) == output
