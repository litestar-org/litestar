from litestar.contrib.pydantic import PydanticDTO
from litestar.controller.generic import GenericController
from litestar.repository.testing.generic_mock_repository import GenericSyncMockRepository
from tests import PydanticPerson


def test_generic_controller_get_generic_annotation() -> None:
    repo = GenericSyncMockRepository[PydanticPerson]

    class TestGenericController(GenericController[PydanticPerson, repo]):  # type: ignore
        path = "/"
        create_dto = PydanticDTO[PydanticPerson]
        update_dto = PydanticDTO[PydanticPerson]

    generic_annotations = TestGenericController.get_generic_annotations()
    assert generic_annotations
    assert len(generic_annotations) == 2
    assert generic_annotations[0] == PydanticPerson
    assert generic_annotations[1] == repo
