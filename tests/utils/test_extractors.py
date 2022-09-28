from typing import Any, List

import pytest
from starlette.status import HTTP_200_OK

from starlite import Cookie, MediaType, Request, RequestEncodingType, Response
from starlite.connection import empty_receive
from starlite.testing import RequestFactory
from starlite.utils import ConnectionDataExtractor
from starlite.utils.extractors import ResponseDataExtractor

factory = RequestFactory()


async def test_connection_data_extractor() -> None:
    request = factory.post(
        path="/a/b/c",
        headers={"Common": "abc", "Special": "123", "Content-Type": "application/json; charset=utf-8"},
        cookies=[Cookie(key="regular"), Cookie(key="auth")],
        query_params={"first": ["1", "2", "3"], "second": ["jeronimo"]},
        data={"hello": "world"},
    )
    request.scope["path_params"] = {"first": "10", "second": "20", "third": "30"}
    extractor = ConnectionDataExtractor(parse_body=True, parse_query=True)
    extracted_data = extractor(request)
    assert await extracted_data["body"] == await request.json()
    assert extracted_data["content_type"] == request.content_type
    assert extracted_data["headers"] == dict(request.headers)
    assert extracted_data["headers"] == dict(request.headers)
    assert extracted_data["path"] == request.scope["path"]
    assert extracted_data["path"] == request.scope["path"]
    assert extracted_data["path_params"] == request.scope["path_params"]
    assert extracted_data["query"] == request.query_params
    assert extracted_data["scheme"] == request.scope["scheme"]


def test_parse_query() -> None:
    request = factory.post(
        path="/a/b/c",
        query_params={"first": ["1", "2", "3"], "second": ["jeronimo"]},
    )
    assert ConnectionDataExtractor(parse_query=True)(request)["query"] == request.query_params
    assert ConnectionDataExtractor(parse_query=False)(request)["query"] == request.scope["query_string"]


async def test_parse_json_data() -> None:
    request = factory.post(path="/a/b/c", data={"hello": "world"})
    assert await ConnectionDataExtractor(parse_body=True)(request)["body"] == await request.json()
    assert await ConnectionDataExtractor(parse_body=False)(request)["body"] == await request.body()


async def test_parse_form_data() -> None:
    request = factory.post(path="/a/b/c", data={"file": b"123"}, request_media_type=RequestEncodingType.MULTI_PART)
    assert await ConnectionDataExtractor(parse_body=True)(request)["body"] == dict(await request.form())


async def test_parse_url_encoded() -> None:
    request = factory.post(path="/a/b/c", data={"key": "123"}, request_media_type=RequestEncodingType.URL_ENCODED)
    assert await ConnectionDataExtractor(parse_body=True)(request)["body"] == dict(await request.form())


@pytest.mark.parametrize(
    "req", [factory.get(path="/", headers={"Special": "123"}), factory.get(path="/", headers={"special": "123"})]
)
def test_request_extraction_header_obfuscation(req: Request[Any, Any]) -> None:
    extractor = ConnectionDataExtractor(obfuscate_headers={"special"})
    extracted_data = extractor(req)
    assert extracted_data["headers"] == {"special": "*****"}


@pytest.mark.parametrize(
    "req, key",
    [
        (factory.get(path="/", cookies=[Cookie(key="special")]), "special"),
        (factory.get(path="/", cookies=[Cookie(key="Special")]), "Special"),
    ],
)
def test_request_extraction_cookie_obfuscation(req: Request[Any, Any], key: str) -> None:
    extractor = ConnectionDataExtractor(obfuscate_cookies={"special"})
    extracted_data = extractor(req)
    assert extracted_data["cookies"] == {"Path": "/", "SameSite": "lax", key: "*****"}


async def test_response_data_extractor() -> None:
    headers = {"common": "abc", "special": "123", "content-type": "application/json; charset=utf-8"}
    cookies = [Cookie(key="regular"), Cookie(key="auth")]
    response = Response(
        media_type=MediaType.JSON,
        status_code=HTTP_200_OK,
        content={"hello": "world"},
        headers=headers,
    )
    for cookie in cookies:
        response.set_cookie(**cookie.dict(exclude={"documentation_only", "description"}))
    extractor = ResponseDataExtractor()
    messages: List["Any"] = []

    async def send(message: "Any") -> None:
        messages.append(message)

    await response({}, empty_receive, send)

    assert len(messages) == 2
    extracted_data = extractor(messages)  # type: ignore
    assert extracted_data["status_code"] == HTTP_200_OK
    assert extracted_data["body"] == b'{"hello":"world"}'
    assert extracted_data["headers"] == {**headers, "content-length": "17"}
    assert extracted_data["cookies"] == {"Path": "/", "SameSite": "lax", "auth": "None", "regular": "None"}
