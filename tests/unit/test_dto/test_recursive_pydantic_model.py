from __future__ import annotations

from pydantic import BaseModel

from litestar import Litestar, get
from litestar.dto import DTOConfig
from litestar.plugins.pydantic import PydanticDTO
from litestar.testing import TestClient


class Node(BaseModel):
    name: str
    child: Node | None = None


def test_self_referencing_pydantic_model_does_not_crash() -> None:
    Node.model_rebuild()
    node = Node(name="root", child=Node(name="child"))
    assert node.name == "root"
    assert node.child is not None
    assert node.child.name == "child"


@get("/node")
async def get_node() -> Node:
    return Node(name="root", child=Node(name="child"))


def test_self_referencing_pydantic_model_openapi_schema() -> None:
    Node.model_rebuild()
    app = Litestar(route_handlers=[get_node])
    schema = app.openapi_schema
    assert schema is not None
    assert schema.components is not None
    assert schema.components.schemas is not None
    assert "Node" in schema.components.schemas

    node_schema = schema.components.schemas["Node"]
    assert node_schema is not None
    properties = node_schema.properties
    assert properties is not None
    assert "child" in properties
    child_schema = properties["child"]
    assert child_schema is not None
    child_schema_dict = child_schema.to_schema()
    assert "$ref" in str(child_schema_dict)
    assert "Node" in str(child_schema_dict)


class User(BaseModel):
    name: str
    group: Group | None = None


class Group(BaseModel):
    name: str
    users: list[User] = []


@get("/group")
async def get_group() -> Group:
    return Group(name="admins", users=[User(name="alice")])


def test_mutually_recursive_pydantic_model_openapi_schema() -> None:
    User.model_rebuild()
    Group.model_rebuild()
    app = Litestar(route_handlers=[get_group])
    schema = app.openapi_schema
    assert schema is not None
    assert schema.components is not None
    assert schema.components.schemas is not None
    assert "User" in schema.components.schemas
    assert "Group" in schema.components.schemas
    user_schema = schema.components.schemas["User"]
    group_schema = schema.components.schemas["Group"]
    user_props = user_schema.properties
    assert user_props is not None
    assert "group" in user_props
    group_field = user_props["group"]
    group_field_dict = group_field.to_schema()
    assert "$ref" in str(group_field_dict)
    assert "Group" in str(group_field_dict)
    group_props = group_schema.properties
    assert group_props is not None
    assert "users" in group_props
    users_field = group_props["users"]
    users_field_dict = users_field.to_schema()
    assert "$ref" in str(users_field_dict)
    assert "User" in str(users_field_dict)


class NodeDTO(PydanticDTO[Node]):
    config = DTOConfig()


def test_recursive_model_dto_generation() -> None:
    Node.model_rebuild()
    app = Litestar(route_handlers=[get_node], dto=NodeDTO)
    assert app is not None


def test_recursive_model_dto_response_serialization() -> None:
    Node.model_rebuild()
    app = Litestar(route_handlers=[get_node], dto=NodeDTO)
    with TestClient(app=app) as client:
        response = client.get("/node")
        assert response.status_code == 200
        assert response.json() == {
            "name": "root",
            "child": {
                "name": "child",
            },
        }


class UserDTO(PydanticDTO[User]):
    config = DTOConfig()


class GroupDTO(PydanticDTO[Group]):
    config = DTOConfig()


def test_mutual_recursive_dto_response_serialization() -> None:
    User.model_rebuild()
    Group.model_rebuild()
    app = Litestar(
        route_handlers=[get_group],
        dto=GroupDTO,
    )
    with TestClient(app=app) as client:
        response = client.get("/group")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "admins"
    assert isinstance(data["users"], list)
    assert data["users"][0]["name"] == "alice"
    assert "group" not in data["users"][0] or data["users"][0]["group"] is None


def test_deeply_nested_recursive_dto_response_serialization() -> None:
    Node.model_rebuild()

    @get("/deep-node")
    async def get_deep_node() -> Node:
        return Node(
            name="level-1",
            child=Node(
                name="level-2",
                child=Node(
                    name="level-3",
                    child=Node(name="level-4"),
                ),
            ),
        )

    app = Litestar(route_handlers=[get_deep_node], dto=NodeDTO)
    with TestClient(app=app) as client:
        response = client.get("/deep-node")
        assert response.status_code == 200
        assert response.json() == {
            "name": "level-1",
            "child": {
                "name": "level-2",
            },
        }


def test_recursive_dto_preserves_expected_fields() -> None:
    Node.model_rebuild()
    app = Litestar(route_handlers=[get_node], dto=NodeDTO)
    with TestClient(app=app) as client:
        response = client.get("/node")
        data = response.json()
        assert response.status_code == 200
        assert set(data.keys()) == {"name", "child"}
        assert set(data["child"].keys()) == {"name"}
        assert data["name"] == "root"
        assert data["child"]["name"] == "child"
