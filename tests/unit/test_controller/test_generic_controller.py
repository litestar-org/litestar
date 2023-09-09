# ruff: noqa: UP007, UP006
from __future__ import annotations

from typing import Any, List
from urllib.parse import urlencode

import pytest

from litestar import HttpMethod, Litestar, MediaType, get
from litestar.contrib.pydantic import PydanticDTO
from litestar.controller.generic import GENERIC_METHOD_NAMES, GenericController
from litestar.exceptions import ImproperlyConfiguredException
from litestar.handlers import HTTPRouteHandler
from litestar.repository import AbstractAsyncRepository, FilterTypes
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT
from litestar.testing import create_test_client
from litestar.types import Method
from tests import PydanticPerson, PydanticPersonFactory


def _get_generic_handlers(
    app: Litestar, controller_type: type[GenericController]
) -> dict[str, dict[Method, HTTPRouteHandler]]:
    return {k: v for k, v in app.route_handler_method_map.items() if k.startswith(controller_type.path)}  # type: ignore


class PersonRepository(AbstractAsyncRepository[PydanticPerson]):
    def __init__(self, **kwargs: Any) -> None:
        """Repository constructors accept arbitrary kwargs."""
        self.request = kwargs.pop("request", None)
        super().__init__()

    async def add_many(self, data: list[PydanticPerson]) -> list[PydanticPerson]:
        return [
            PydanticPersonFactory.build(**(datum.model_dump() if hasattr(datum, "model_dump") else datum.dict()))
            for datum in data
        ]

    async def add(self, data: PydanticPerson) -> PydanticPerson:
        return PydanticPersonFactory.build(**(data.model_dump() if hasattr(data, "model_dump") else data.dict()))

    async def count(self, *filters: FilterTypes, **kwargs: Any) -> int:
        return 0

    async def exists(self, *filters: FilterTypes, **kwargs: Any) -> bool:
        return False

    async def delete(self, item_id: Any) -> PydanticPerson:
        return PydanticPersonFactory.build(id=item_id)

    async def delete_many(self, item_ids: list[Any]) -> list[PydanticPerson]:
        return [PydanticPersonFactory.build(id=item_id) for item_id in item_ids]

    async def get(self, item_id: Any, **kwargs: Any) -> PydanticPerson:
        return PydanticPersonFactory.build(id=item_id, **kwargs)

    async def get_one(self, **kwargs: Any) -> PydanticPerson:
        return PydanticPersonFactory.build(**kwargs)

    async def get_or_create(self, **kwargs: Any) -> tuple[PydanticPerson, bool]:
        return PydanticPersonFactory.build(**kwargs), True

    async def get_one_or_none(self, **kwargs: Any) -> PydanticPerson | None:
        return PydanticPersonFactory.build(**kwargs)

    async def update(self, data: PydanticPerson) -> PydanticPerson:
        return PydanticPersonFactory.build(**(data.model_dump() if hasattr(data, "model_dump") else data.dict()))

    async def update_many(self, data: list[PydanticPerson]) -> list[PydanticPerson]:
        return [
            PydanticPersonFactory.build(**(datum.model_dump() if hasattr(datum, "model_dump") else datum.dict()))
            for datum in data
        ]

    async def upsert(self, data: PydanticPerson) -> PydanticPerson:
        return PydanticPersonFactory.build(**(data.model_dump() if hasattr(data, "model_dump") else data.dict()))

    async def upsert_many(self, data: list[PydanticPerson]) -> list[PydanticPerson]:
        return [
            PydanticPersonFactory.build(**(datum.model_dump() if hasattr(datum, "model_dump") else datum.dict()))
            for datum in data
        ]

    async def list_and_count(self, *filters: FilterTypes, **kwargs: Any) -> tuple[list[PydanticPerson], int]:
        return PydanticPersonFactory.batch(size=5, **kwargs), 5

    async def list(self, *filters: FilterTypes, **kwargs: Any) -> list[PydanticPerson]:
        return PydanticPersonFactory.batch(size=5, **kwargs)

    async def filter_collection_by_kwargs(self, collection: Any, /, **kwargs: Any) -> Any:  # type: ignore
        pass


class TestGenericController(GenericController[PydanticPerson, str]):
    path = "/generic-controller"
    repository_type = PersonRepository
    create_dto = PydanticDTO[PydanticPerson]
    update_dto = PydanticDTO[PydanticPerson]


def test_generic_controller_get_generic_annotation() -> None:
    generic_annotations = TestGenericController.get_generic_annotations()
    assert generic_annotations
    assert len(generic_annotations) == 2
    assert generic_annotations[0] == PydanticPerson
    assert generic_annotations[1] == str


def test_generic_controller_raises_when_not_annotated() -> None:
    class _Controller(GenericController):
        pass

    with pytest.raises(ImproperlyConfiguredException):
        _Controller.get_generic_annotations()


def test_replaces_generic_parameters() -> None:
    app = Litestar(route_handlers=[TestGenericController])

    for mapping in _get_generic_handlers(app, TestGenericController).values():
        for handler in [v for k, v in mapping.items() if k not in ("OPTIONS", "HEAD")]:
            if "data" in handler.fn.__annotations__:
                if "many" in handler.fn.value.__name__:  # type: ignore[union-attr]
                    assert handler.fn.value.__annotations__["data"] == list[PydanticPerson]
                else:
                    assert handler.fn.value.__annotations__["data"] == PydanticPerson
            if "return" in handler.fn.value.__annotations__:
                if "many" in handler.fn.value.__name__:  # type: ignore[union-attr]
                    if "delete" in handler.fn.value.__name__:  # type: ignore[union-attr]
                        assert handler.fn.value.__annotations__["return"] in ("None", None, type(None))
                    else:
                        assert handler.fn.value.__annotations__["return"] == List[PydanticPerson]
                elif "delete" in handler.fn.value.__name__:  # type: ignore[union-attr]
                    assert handler.fn.value.__annotations__["return"] in ("None", None, type(None))
                else:
                    assert handler.fn.value.__annotations__["return"] == PydanticPerson
            if "item_id" in handler.fn.value.__annotations__:
                assert handler.fn.value.__annotations__["item_id"] == str
            if "item_ids" in handler.fn.value.__annotations__:
                assert handler.fn.value.__annotations__["item_ids"] == List[str]


@pytest.mark.parametrize(
    "method_name, expected_path, expected_operation_id, expected_method",
    tuple(
        (
            method_name,
            getattr(TestGenericController, f"{method_name}_handler_path").replace("path_param_type", "str"),
            getattr(TestGenericController, f"{method_name}_operation_id").replace(
                "{model_name}", PydanticPerson.__name__
            ),
            getattr(TestGenericController, f"{method_name}_http_method"),
        )
        for method_name in GENERIC_METHOD_NAMES
    ),
)
def test_default_attributes(
    method_name: str, expected_path: str, expected_operation_id: str, expected_method: HttpMethod
) -> None:
    path = (TestGenericController.path + expected_path).rstrip("/")
    mapping = _get_generic_handlers(Litestar(route_handlers=[TestGenericController]), TestGenericController)[path]
    handler = mapping[expected_method.value]
    assert handler.paths == {expected_path}
    assert handler.operation_id == expected_operation_id
    assert handler.http_methods == {expected_method}


def test_get_instance() -> None:
    with create_test_client(TestGenericController) as client:
        response = client.get(f"{TestGenericController.path}/abc")
        assert response.status_code == HTTP_200_OK
        assert PydanticPerson(**response.json()).id == "abc"


def test_create_instance() -> None:
    with create_test_client(TestGenericController) as client:
        instance = PydanticPersonFactory.build()
        response = client.post(
            TestGenericController.path,
            json=instance.model_dump() if hasattr(instance, "model_dump") else instance.dict(),
        )
        assert response.status_code == HTTP_201_CREATED
        assert PydanticPerson(**response.json()).id == instance.id


def test_update_instance() -> None:
    with create_test_client(TestGenericController) as client:
        instance = PydanticPersonFactory.build()
        response = client.patch(
            TestGenericController.path,
            json=instance.model_dump() if hasattr(instance, "model_dump") else instance.dict(),
        )
        assert response.status_code == HTTP_200_OK
        assert PydanticPerson(**response.json()).id == instance.id


def test_delete_instance() -> None:
    with create_test_client(TestGenericController) as client:
        response = client.delete(f"{TestGenericController.path}/abc")
        assert response.status_code == HTTP_204_NO_CONTENT


def test_get_many() -> None:
    with create_test_client(TestGenericController) as client:
        item_ids = {"item_ids": ["abc", "def", "ghi", "jkl", "mno"]}
        response = client.get(f"{TestGenericController.path}?{urlencode(item_ids, doseq=True)}")
        assert response.status_code == HTTP_200_OK
        assert len(response.json()) == 5


def test_create_many() -> None:
    with create_test_client(TestGenericController) as client:
        instances = PydanticPersonFactory.batch(size=5)
        response = client.post(
            f"{TestGenericController.path}/bulk-create",
            json=[
                instance.model_dump() if hasattr(instance, "model_dump") else instance.dict() for instance in instances
            ],
        )
        assert response.status_code == HTTP_201_CREATED
        assert len(response.json()) == 5


def test_update_many() -> None:
    with create_test_client(TestGenericController) as client:
        instances = PydanticPersonFactory.batch(size=5)
        response = client.patch(
            f"{TestGenericController.path}/bulk-update",
            json=[
                instance.model_dump() if hasattr(instance, "model_dump") else instance.dict() for instance in instances
            ],
        )
        assert response.status_code == HTTP_200_OK
        assert len(response.json()) == 5


def test_delete_many() -> None:
    with create_test_client(TestGenericController) as client:
        item_ids = {"item_ids": ["abc", "def", "ghi", "jkl", "mno"]}
        response = client.delete(f"{TestGenericController.path}/bulk-delete" + f"?{urlencode(item_ids, doseq=True)}")
        assert response.status_code == HTTP_204_NO_CONTENT


def test_method_overriding() -> None:
    class OverrideController(TestGenericController):
        @get("/override", media_type=MediaType.TEXT)
        def get_instance(self) -> str:  # type: ignore[override]
            return "override"

    with create_test_client(OverrideController) as client:
        response = client.get(f"{OverrideController.path}/override")
        assert response.status_code == HTTP_200_OK
        assert response.text == "override"


def test_schema_generation() -> None:
    app = Litestar(route_handlers=[TestGenericController])
    schema = app.openapi_schema.to_schema()
    paths = schema.get("paths")
    assert paths

    generic_controller_base_paths = paths.get("/generic-controller")
    assert generic_controller_base_paths
    assert generic_controller_base_paths == {
        "get": {
            "deprecated": False,
            "operationId": "getManyPydanticPerson",
            "parameters": [
                {
                    "allowEmptyValue": False,
                    "allowReserved": False,
                    "deprecated": False,
                    "in": "query",
                    "name": "item_ids",
                    "required": True,
                    "schema": {"items": {"type": "string"}, "type": "array"},
                }
            ],
            "responses": {
                "200": {
                    "content": {
                        "application/json": {
                            "schema": {"items": {"$ref": "#/components/schemas/PydanticPerson"}, "type": "array"}
                        }
                    },
                    "description": "Request fulfilled, document follows",
                    "headers": {},
                },
                "400": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "description": "Validation Exception",
                                "examples": [{"detail": "Bad Request", "extra": {}, "status_code": 400}],
                                "properties": {
                                    "detail": {"type": "string"},
                                    "extra": {"additionalProperties": {}, "type": ["null", "object", "array"]},
                                    "status_code": {"type": "integer"},
                                },
                                "required": ["detail", "status_code"],
                                "type": "object",
                            }
                        }
                    },
                    "description": "Bad request syntax or unsupported method",
                },
            },
            "summary": "GetMany",
        },
        "patch": {
            "deprecated": False,
            "operationId": "updatePydanticPerson",
            "requestBody": {
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/PydanticPerson"}}},
                "required": True,
            },
            "responses": {
                "200": {
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/PydanticPerson"}}},
                    "description": "Request fulfilled, document follows",
                    "headers": {},
                },
                "400": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "description": "Validation Exception",
                                "examples": [{"detail": "Bad Request", "extra": {}, "status_code": 400}],
                                "properties": {
                                    "detail": {"type": "string"},
                                    "extra": {"additionalProperties": {}, "type": ["null", "object", "array"]},
                                    "status_code": {"type": "integer"},
                                },
                                "required": ["detail", "status_code"],
                                "type": "object",
                            }
                        }
                    },
                    "description": "Bad request syntax or unsupported method",
                },
            },
            "summary": "UpdateInstance",
        },
        "post": {
            "deprecated": False,
            "operationId": "createPydanticPerson",
            "requestBody": {
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/PydanticPerson"}}},
                "required": True,
            },
            "responses": {
                "201": {
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/PydanticPerson"}}},
                    "description": "Document created, URL follows",
                    "headers": {},
                },
                "400": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "description": "Validation Exception",
                                "examples": [{"detail": "Bad Request", "extra": {}, "status_code": 400}],
                                "properties": {
                                    "detail": {"type": "string"},
                                    "extra": {"additionalProperties": {}, "type": ["null", "object", "array"]},
                                    "status_code": {"type": "integer"},
                                },
                                "required": ["detail", "status_code"],
                                "type": "object",
                            }
                        }
                    },
                    "description": "Bad request syntax or unsupported method",
                },
            },
            "summary": "CreateInstance",
        },
    }
    generic_controller_bulk_create_paths = paths.get("/generic-controller/bulk-create")
    assert generic_controller_bulk_create_paths
    assert generic_controller_bulk_create_paths == {
        "post": {
            "summary": "CreateMany",
            "operationId": "createManyPydanticPerson",
            "requestBody": {
                "content": {
                    "application/json": {
                        "schema": {"items": {"$ref": "#/components/schemas/PydanticPerson"}, "type": "array"}
                    }
                },
                "required": True,
            },
            "responses": {
                "201": {
                    "description": "Document created, URL follows",
                    "headers": {},
                    "content": {
                        "application/json": {
                            "schema": {"items": {"$ref": "#/components/schemas/PydanticPerson"}, "type": "array"}
                        }
                    },
                },
                "400": {
                    "description": "Bad request syntax or unsupported method",
                    "content": {
                        "application/json": {
                            "schema": {
                                "properties": {
                                    "status_code": {"type": "integer"},
                                    "detail": {"type": "string"},
                                    "extra": {"additionalProperties": {}, "type": ["null", "object", "array"]},
                                },
                                "type": "object",
                                "required": ["detail", "status_code"],
                                "description": "Validation Exception",
                                "examples": [{"status_code": 400, "detail": "Bad Request", "extra": {}}],
                            }
                        }
                    },
                },
            },
            "deprecated": False,
        }
    }

    generic_controller_instance_paths = paths.get("/generic-controller/{item_id}")
    assert generic_controller_instance_paths
    assert generic_controller_instance_paths == {
        "get": {
            "summary": "GetInstance",
            "operationId": "getPydanticPerson",
            "parameters": [
                {
                    "name": "item_id",
                    "in": "path",
                    "schema": {"type": "string"},
                    "required": True,
                    "deprecated": False,
                    "allowEmptyValue": False,
                    "allowReserved": False,
                }
            ],
            "responses": {
                "200": {
                    "description": "Request fulfilled, document follows",
                    "headers": {},
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/PydanticPerson"}}},
                },
                "400": {
                    "description": "Bad request syntax or unsupported method",
                    "content": {
                        "application/json": {
                            "schema": {
                                "properties": {
                                    "status_code": {"type": "integer"},
                                    "detail": {"type": "string"},
                                    "extra": {"additionalProperties": {}, "type": ["null", "object", "array"]},
                                },
                                "type": "object",
                                "required": ["detail", "status_code"],
                                "description": "Validation Exception",
                                "examples": [{"status_code": 400, "detail": "Bad Request", "extra": {}}],
                            }
                        }
                    },
                },
            },
            "deprecated": False,
        },
        "delete": {
            "summary": "DeleteInstance",
            "operationId": "deletePydanticPerson",
            "parameters": [
                {
                    "name": "item_id",
                    "in": "path",
                    "schema": {"type": "string"},
                    "required": True,
                    "deprecated": False,
                    "allowEmptyValue": False,
                    "allowReserved": False,
                }
            ],
            "responses": {
                "204": {"description": "Request fulfilled, nothing follows", "headers": {}},
                "400": {
                    "description": "Bad request syntax or unsupported method",
                    "content": {
                        "application/json": {
                            "schema": {
                                "properties": {
                                    "status_code": {"type": "integer"},
                                    "detail": {"type": "string"},
                                    "extra": {"additionalProperties": {}, "type": ["null", "object", "array"]},
                                },
                                "type": "object",
                                "required": ["detail", "status_code"],
                                "description": "Validation Exception",
                                "examples": [{"status_code": 400, "detail": "Bad Request", "extra": {}}],
                            }
                        }
                    },
                },
            },
            "deprecated": False,
        },
    }

    generic_controller_bulk_delete_paths = paths.get("/generic-controller/bulk-delete")
    assert generic_controller_bulk_delete_paths
    assert generic_controller_bulk_delete_paths == {
        "delete": {
            "summary": "DeleteMany",
            "operationId": "deleteManyPydanticPerson",
            "parameters": [
                {
                    "name": "item_ids",
                    "in": "query",
                    "schema": {"items": {"type": "string"}, "type": "array"},
                    "required": True,
                    "deprecated": False,
                    "allowEmptyValue": False,
                    "allowReserved": False,
                }
            ],
            "responses": {
                "204": {"description": "Request fulfilled, nothing follows", "headers": {}},
                "400": {
                    "description": "Bad request syntax or unsupported method",
                    "content": {
                        "application/json": {
                            "schema": {
                                "properties": {
                                    "status_code": {"type": "integer"},
                                    "detail": {"type": "string"},
                                    "extra": {"additionalProperties": {}, "type": ["null", "object", "array"]},
                                },
                                "type": "object",
                                "required": ["detail", "status_code"],
                                "description": "Validation Exception",
                                "examples": [{"status_code": 400, "detail": "Bad Request", "extra": {}}],
                            }
                        }
                    },
                },
            },
            "deprecated": False,
        }
    }

    generic_controller_bulk_update_paths = paths.get("/generic-controller/bulk-update")
    assert generic_controller_bulk_update_paths
    assert generic_controller_bulk_update_paths == {
        "patch": {
            "summary": "UpdateMany",
            "operationId": "updateManyPydanticPerson",
            "requestBody": {
                "content": {
                    "application/json": {
                        "schema": {"items": {"$ref": "#/components/schemas/PydanticPerson"}, "type": "array"}
                    }
                },
                "required": True,
            },
            "responses": {
                "200": {
                    "description": "Request fulfilled, document follows",
                    "headers": {},
                    "content": {
                        "application/json": {
                            "schema": {"items": {"$ref": "#/components/schemas/PydanticPerson"}, "type": "array"}
                        }
                    },
                },
                "400": {
                    "description": "Bad request syntax or unsupported method",
                    "content": {
                        "application/json": {
                            "schema": {
                                "properties": {
                                    "status_code": {"type": "integer"},
                                    "detail": {"type": "string"},
                                    "extra": {"additionalProperties": {}, "type": ["null", "object", "array"]},
                                },
                                "type": "object",
                                "required": ["detail", "status_code"],
                                "description": "Validation Exception",
                                "examples": [{"status_code": 400, "detail": "Bad Request", "extra": {}}],
                            }
                        }
                    },
                },
            },
            "deprecated": False,
        }
    }
