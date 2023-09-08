from __future__ import annotations

from litestar import Litestar
from litestar.contrib.pydantic import PydanticDTO
from litestar.controller.generic import GenericController, ItemIdsRequestBody
from litestar.handlers import HTTPRouteHandler
from litestar.repository.testing.generic_mock_repository import GenericSyncMockRepository
from litestar.types import Method
from tests import PydanticPerson


def _get_generic_handlers(
    app: Litestar, controller_type: type[GenericController]
) -> dict[str, dict[Method, HTTPRouteHandler]]:
    return {k: v for k, v in app.route_handler_method_map.items() if k.startswith(controller_type.path)}  # type: ignore


def test_generic_controller_get_generic_annotation() -> None:
    GenericSyncMockRepository[PydanticPerson]

    class TestGenericController(GenericController[PydanticPerson, str]):
        path = "/"
        create_dto = PydanticDTO[PydanticPerson]
        update_dto = PydanticDTO[PydanticPerson]

    generic_annotations = TestGenericController.get_generic_annotations()
    assert generic_annotations
    assert len(generic_annotations) == 2
    assert generic_annotations[0] == PydanticPerson
    assert generic_annotations[1] == str
    assert TestGenericController.model_type == PydanticPerson  # type: ignore
    assert TestGenericController.id_attribute_type == str  # type: ignore


def test_replaces_generic_parameters() -> None:
    GenericSyncMockRepository[PydanticPerson]

    class TestGenericController(GenericController[PydanticPerson, str]):
        path = "/generic-controller"
        create_dto = PydanticDTO[PydanticPerson]
        update_dto = PydanticDTO[PydanticPerson]

    app = Litestar(route_handlers=[TestGenericController])

    for mapping in _get_generic_handlers(app, TestGenericController).values():
        for handler in [v for k, v in mapping.items() if k not in ("OPTIONS", "HEAD")]:
            if "data" in handler.fn.__annotations__:
                if "many" in handler.fn.value.__name__:  # type: ignore[union-attr]
                    if handler.fn.value.__name__ == "delete_many":  # type: ignore[union-attr]
                        assert handler.fn.value.__annotations__["data"] == ItemIdsRequestBody[str]
                    else:
                        assert handler.fn.value.__annotations__["data"] == list[PydanticPerson]
                else:
                    assert handler.fn.value.__annotations__["data"] == PydanticPerson
            if "return" in handler.fn.value.__annotations__:
                if "many" in handler.fn.value.__name__:  # type: ignore[union-attr]
                    if "delete" in handler.fn.value.__name__:  # type: ignore[union-attr]
                        assert handler.fn.value.__annotations__["return"] in ("None", None)
                    else:
                        assert handler.fn.value.__annotations__["return"] == list[PydanticPerson]
                elif "delete" in handler.fn.value.__name__:  # type: ignore[union-attr]
                    assert handler.fn.value.__annotations__["return"] in ("None", None)
                else:
                    assert handler.fn.value.__annotations__["return"] == PydanticPerson
            if "item_id" in handler.fn.value.__annotations__:
                assert handler.fn.value.__annotations__["item_id"] == str
            if "item_ids" in handler.fn.value.__annotations__:
                assert handler.fn.value.__annotations__["item_ids"] == list[str]
