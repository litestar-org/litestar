from asyncio import sleep
from typing import Any

import orjson

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse

app = Starlette()

## default json


@app.route(path="/async-json-no-params", methods=["GET"])
async def async_json_no_params(_) -> JSONResponse:
    await sleep(0.0000000001)
    return JSONResponse({"message": "Hello, world!"})


@app.route(path="/sync-json-no-params", methods=["GET"])
def sync_json_no_params(_) -> JSONResponse:
    return JSONResponse({"message": "Hello, world!"})


@app.route(path="/async-json/{first:str}", methods=["GET"])
async def async_json_path_param(request: Request) -> JSONResponse:
    await sleep(0.0000000001)
    return JSONResponse({"message": request.path_params["first"]})


@app.route(path="/sync-json/{first:str}", methods=["GET"])
def sync_json_path_param(request: Request) -> JSONResponse:
    return JSONResponse({"message": request.path_params["first"]})


@app.route(path="/async-json-query-param", methods=["GET"])
async def async_json_query_param(request: Request) -> JSONResponse:
    await sleep(0.0000000001)
    return JSONResponse({"message": request.query_params["first"]})


@app.route(path="/sync-json-query-param", methods=["GET"])
def sync_json_query_param(request: Request) -> JSONResponse:
    return JSONResponse({"message": request.query_params["first"]})


@app.route(path="/async-json-mixed-params/{second:str}", methods=["GET"])
async def async_json_mixed_params(request: Request) -> JSONResponse:
    await sleep(0.0000000001)
    return JSONResponse(
        {"message": request.query_params["first"] + request.path_params["second"]}
    )


@app.route(path="/sync-json-mixed-params/{second:str}", methods=["GET"])
def sync_json_mixed_params(request: Request) -> JSONResponse:
    return JSONResponse(
        {"message": request.query_params["first"] + request.path_params["second"]}
    )


## orjson

class ORJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return orjson.dumps(content)


class ORJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return orjson.dumps(content)


@app.route(path="/async-json-no-params", methods=["GET"])
async def async_json_no_params(_) -> ORJSONResponse:
    await sleep(0.0000000001)
    return ORJSONResponse({"message": "Hello, world!"})


@app.route(path="/sync-json-no-params", methods=["GET"])
def sync_json_no_params(_) -> ORJSONResponse:
    return ORJSONResponse({"message": "Hello, world!"})


@app.route(path="/async-json/{first:str}", methods=["GET"])
async def async_json_path_param(request: Request) -> ORJSONResponse:
    await sleep(0.0000000001)
    return ORJSONResponse({"message": request.path_params["first"]})


@app.route(path="/sync-json/{first:str}", methods=["GET"])
def sync_json_path_param(request: Request) -> ORJSONResponse:
    return ORJSONResponse({"message": request.path_params["first"]})


@app.route(path="/async-json-query-param", methods=["GET"])
async def async_json_query_param(request: Request) -> ORJSONResponse:
    await sleep(0.0000000001)
    return ORJSONResponse({"message": request.query_params["first"]})


@app.route(path="/sync-json-query-param", methods=["GET"])
def sync_json_query_param(request: Request) -> ORJSONResponse:
    return ORJSONResponse({"message": request.query_params["first"]})


@app.route(path="/async-json-mixed-params/{second:str}", methods=["GET"])
async def async_json_mixed_params(request: Request) -> ORJSONResponse:
    await sleep(0.0000000001)
    return ORJSONResponse(
        {"message": request.query_params["first"] + request.path_params["second"]}
    )


@app.route(path="/sync-json-mixed-params/{second:str}", methods=["GET"])
def sync_json_mixed_params(request: Request) -> ORJSONResponse:
    return ORJSONResponse(
        {"message": request.query_params["first"] + request.path_params["second"]}
    )


## plain text


@app.route(path="/async-plaintext-no-params", methods=["GET"])
async def async_plaintext_no_params(_) -> str:
    await sleep(0.0000000001)
    return PlainTextResponse("Hello, world!")


@app.route(path="/sync-plaintext-no-params", methods=["GET"])
def sync_plaintext_no_params(_) -> str:
    return PlainTextResponse("Hello, world!")


@app.route(path="/async-plaintext/{first:str}", methods=["GET"])
async def async_plaintext_path_param(request: Request) -> str:
    await sleep(0.0000000001)
    return PlainTextResponse(request.path_params["first"])


@app.route(path="/sync-plaintext/{first:str}", methods=["GET"])
def sync_plaintext_path_param(request: Request) -> str:
    return PlainTextResponse(request.path_params["first"])


@app.route(path="/async-plaintext-query-param", methods=["GET"])
async def async_plaintext_query_param(request: Request) -> str:
    await sleep(0.0000000001)
    return PlainTextResponse(request.query_params["first"])


@app.route(path="/sync-plaintext-query-param", methods=["GET"])
def sync_plaintext_query_param(request: Request) -> str:
    return PlainTextResponse(request.query_params["first"])


@app.route(path="/async-plaintext-mixed-params/{second:str}", methods=["GET"])
async def async_plaintext_mixed_params(request: Request) -> str:
    await sleep(0.0000000001)
    return PlainTextResponse(
        request.query_params["first"] + request.path_params["second"]
    )


@app.route(path="/sync-plaintext-mixed-params/{second:str}", methods=["GET"])
def sync_plaintext_mixed_params(request: Request) -> str:
    return PlainTextResponse(
        request.query_params["first"] + request.path_params["second"]
    )
