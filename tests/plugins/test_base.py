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


class AModel:
    def __init__(self, name: str) -> None:
        self.name = name

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, type(self)):
            return __o.name == self.name
        return False


class APydanticModel(BaseModel):
    name: str


class APlugin(DummyPlugin[AModel]):
    def to_pydantic_model_class(self, model_class: Type[ModelT], **kwargs: Any) -> Type[BaseModel]:
        assert model_class is AModel
        return APydanticModel

    @staticmethod
    def is_plugin_supported_type(value: Any) -> bool:
        return value is AModel

    def from_pydantic_model_instance(self, model_class: Type[AModel], pydantic_model_instance: BaseModel) -> AModel:
        assert model_class is AModel
        assert isinstance(pydantic_model_instance, APydanticModel)
        return model_class(**pydantic_model_instance.dict())

    def to_dict(self, model_instance: ModelT) -> Dict[str, Any]:
        return dict(model_instance)  # type: ignore

    def from_dict(self, model_class: Type[ModelT], **kwargs: Any) -> ModelT:
        assert model_class is AModel
        return model_class(**kwargs)


@pytest.mark.parametrize(
    ["input", "output"],
    [
        [APydanticModel(name="my name"), AModel(name="my name")],
        [[APydanticModel(name="1"), APydanticModel(name="2")], [AModel(name="1"), AModel(name="2")]],
        [(APydanticModel(name="1"), APydanticModel(name="2")), [AModel(name="1"), AModel(name="2")]],
    ],
)
def test_plugin_mapping_value_to_model_instance(input: Any, output: Any) -> None:
    mapping = PluginMapping(plugin=APlugin(), model_class=AModel)
    assert mapping.get_model_instance_for_value(input) == output
