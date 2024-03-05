import pydantic
import pytest
from pydantic import Field as FieldV2
from pydantic.v1.fields import Field as FieldV1

from litestar import get
from litestar.contrib.pydantic import PydanticPlugin
from litestar.testing import create_test_client


@pytest.mark.parametrize(
    "plugin_params, response",
    (
        (
            {"exclude": {"alias"}},
            {
                "none": None,
                "default": "default",
            },
        ),
        ({"exclude_defaults": True}, {"alias": "prefer_alias"}),
        ({"exclude_none": True}, {"alias": "prefer_alias", "default": "default"}),
        ({"exclude_unset": True}, {"alias": "prefer_alias"}),
        ({"include": {"alias"}}, {"alias": "prefer_alias"}),
        ({"prefer_alias": True}, {"prefer_alias": "prefer_alias", "default": "default", "none": None}),
    ),
    ids=(
        "Exclude alias field",
        "Exclude default fields",
        "Exclude None field",
        "Exclude unset fields",
        "Include alias field",
        "Use alias in response",
    ),
)
def test_app_with_v1_and_v2_models(plugin_params: dict, response: dict) -> None:
    class ModelV1(pydantic.v1.BaseModel):  # pyright: ignore
        alias: str = FieldV1(alias="prefer_alias")
        default: str = "default"
        none: None = None

        class Config:
            allow_population_by_field_name = True

    class ModelV2(pydantic.BaseModel):
        alias: str = FieldV2(serialization_alias="prefer_alias")
        default: str = "default"
        none: None = None

    @get("/v1")
    def handler_v1() -> ModelV1:
        return ModelV1(alias="prefer_alias")  # type: ignore[call-arg]

    @get("/v2")
    def handler_v2() -> ModelV2:
        return ModelV2(alias="prefer_alias")

    with create_test_client([handler_v1, handler_v2], plugins=[PydanticPlugin(**plugin_params)]) as client:
        assert client.get("/v1").json() == response
        assert client.get("/v2").json() == response
