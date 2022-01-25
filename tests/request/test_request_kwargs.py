from typing import Any, Optional, Type

from pydantic import BaseConfig
from pydantic.fields import FieldInfo, ModelField

from starlite import MediaType, State, create_test_client, get


class Config(BaseConfig):
    arbitrary_types_allowed = True


def create_model_field(
    field_name: str, field_type: Type[Any] = dict, field_info: Optional[FieldInfo] = None
) -> ModelField:
    return ModelField(
        name=field_name, type_=field_type, model_config=Config, class_validators=[], field_info=field_info
    )


def test_state():
    @get("/", media_type=MediaType.TEXT)
    def route_handler(state: State) -> str:
        assert state
        state.called = True  # this should not modify the app state
        return state.msg  # this shows injection worked

    with create_test_client(route_handler) as client:
        state = client.app.state
        state.msg = "hello"
        state.called = False
        response = client.get("/")
        assert response.text == "hello"
        assert not state.called
