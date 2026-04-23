from __future__ import annotations

from typing import List, Optional

import pydantic as pydantic_v2
import pytest

from litestar import post
from litestar.dto import DTOConfig
from litestar.plugins.pydantic import PydanticDTO
from litestar.status_codes import HTTP_201_CREATED
from litestar.testing import create_test_client

def test_pydantic_dto_nested_list_validation_issue_4530(use_experimental_dto_backend: bool) -> None:
    # MCVE from issue #4530
    class ToolCallFunction(pydantic_v2.BaseModel):
        name: str
        arguments: str

    class ToolCall(pydantic_v2.BaseModel):
        id: str
        type: str = "function"
        function: ToolCallFunction

    class CreateMessageRequest(pydantic_v2.BaseModel):
        session_id: str
        content: str
        tool_calls: Optional[List[ToolCall]] = None

    class CreateMessageDTO(PydanticDTO[CreateMessageRequest]):
        config = DTOConfig(
            max_nested_depth=10,
            experimental_codegen_backend=use_experimental_dto_backend
        )

    @post("/", dto=CreateMessageDTO)
    async def handler(data: CreateMessageRequest) -> dict:
        return {"tool_count": len(data.tool_calls) if data.tool_calls else 0}

    payload = {
        "session_id": "s1",
        "content": "test",
        "tool_calls": [
            {"id": "call_1", "type": "function", "function": {"name": "fn", "arguments": "{}"}}
        ],
    }

    with create_test_client(handler) as client:
        response = client.post("/", json=payload)
        assert response.status_code == HTTP_201_CREATED
        assert response.json() == {"tool_count": 1}
