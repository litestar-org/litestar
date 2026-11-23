import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).parents[3]
SCRIPT = "import sys; from tests.unit.test_dto.schema_name_apps import main; main(*sys.argv[1:])"
EXPECTED: dict[str, dict[str, Any]] = {
    "single": {
        "components": [
            "CreateUserUserRequestBody",
            "CreateUserUserResponseBody",
            "GetUserUserResponseBody",
            "ListUsersUserResponseBody",
            "PatchUserUserRequestBody",
        ],
        "operations": {
            "GET /users": ["GetUserUserResponseBody"],
            "POST /users": ["CreateUserUserRequestBody", "CreateUserUserResponseBody"],
            "POST /users/partial": ["PatchUserUserRequestBody"],
            "GET /users/all": ["ListUsersUserResponseBody"],
        },
    },
    "nested": {
        "components": [
            "CreatePostPostRequestBody",
            "CreatePostPostResponseBody",
            "CreatePostPostUserRequestBody",
            "CreatePostPostUserResponseBody",
            "CreatePostPost_0TagRequestBody",
            "CreatePostPost_0TagResponseBody",
            "GetPostPostResponseBody",
            "GetPostPostUserResponseBody",
            "GetPostPost_0TagResponseBody",
            "tests.unit.test_dto.schema_name_apps.nested.create_postPostUserRequestBody",
            "tests.unit.test_dto.schema_name_apps.nested.create_postPostUserResponseBody",
            "tests.unit.test_dto.schema_name_apps.nested.get_postPostUserResponseBody",
        ],
        "operations": {
            "GET /posts": ["GetPostPostResponseBody"],
            "POST /posts": ["CreatePostPostRequestBody", "CreatePostPostResponseBody"],
        },
    },
    "same_handler_name": {
        "components": [
            "FetchUserResponseBody",
            "tests.unit.test_dto.schema_name_apps.same_handler_name.SecondController.fetchUserResponseBody",
        ],
        "operations": {
            "GET /first": ["FetchUserResponseBody"],
            "GET /second": [
                "tests.unit.test_dto.schema_name_apps.same_handler_name.SecondController.fetchUserResponseBody"
            ],
        },
    },
    "schema_name": {
        "components": [
            "GetPostPostUserResponseBody",
            "GetPostPost_0TagResponseBody",
            "PublicPost",
            "tests.unit.test_dto.schema_name_apps.schema_name.get_postPostUserResponseBody",
        ],
        "operations": {"GET /posts": ["PublicPost"], "GET /posts/all": ["PublicPost"]},
    },
    "generic_wrapper": {
        "components": ["Envelope_litestar.dto._backend.GetWrappedUserResponseBody_", "GetWrappedUserResponseBody"],
        "operations": {"GET /users": ["Envelope_litestar.dto._backend.GetWrappedUserResponseBody_"]},
    },
    "msgspec_nested": {
        "components": ["GetProductProductMakerResponseBody", "GetProductProductResponseBody"],
        "operations": {"GET /products": ["GetProductProductResponseBody"]},
    },
    "pydantic_nested": {
        "components": ["GetPetPetOwnerResponseBody", "GetPetPetResponseBody"],
        "operations": {"GET /pets": ["GetPetPetResponseBody"]},
    },
}
QUALIFIED_SINGLE: dict[str, Any] = {
    "components": [
        "tests.unit.test_dto.schema_name_apps.single.create_userUserRequestBody",
        "tests.unit.test_dto.schema_name_apps.single.create_userUserResponseBody",
        "tests.unit.test_dto.schema_name_apps.single.get_userUserResponseBody",
        "tests.unit.test_dto.schema_name_apps.single.list_usersUserResponseBody",
        "tests.unit.test_dto.schema_name_apps.single.patch_userUserRequestBody",
    ],
    "operations": {
        "GET /users": ["tests.unit.test_dto.schema_name_apps.single.get_userUserResponseBody"],
        "POST /users": [
            "tests.unit.test_dto.schema_name_apps.single.create_userUserRequestBody",
            "tests.unit.test_dto.schema_name_apps.single.create_userUserResponseBody",
        ],
        "POST /users/partial": ["tests.unit.test_dto.schema_name_apps.single.patch_userUserRequestBody"],
        "GET /users/all": ["tests.unit.test_dto.schema_name_apps.single.list_usersUserResponseBody"],
    },
}


def describe_in_fresh_process(app_id: str, builds: int = 1) -> Any:
    result = subprocess.run(
        [sys.executable, "-c", SCRIPT, app_id, str(builds)], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)


@pytest.mark.parametrize("app_id", sorted(EXPECTED))
def test_component_names_in_fresh_process(app_id: str) -> None:
    if app_id.startswith("pydantic"):
        pytest.importorskip("pydantic")
    assert describe_in_fresh_process(app_id) == EXPECTED[app_id]


def test_second_build_in_same_process_gets_qualified_names() -> None:
    assert describe_in_fresh_process("single", builds=2) == QUALIFIED_SINGLE
