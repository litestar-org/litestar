"""Vortex AI API's main file"""

import json
import os
import random
import secrets
import string
import time
from math import ceil

import openai
import tiktoken
import uvicorn
from dotenv import load_dotenv
from redis_rate_limit import RateLimit, TooManyRequests

import litestar
from litestar import Request, Response
from litestar.config.cors import CORSConfig
from litestar.exceptions import HTTPException
from litestar.middleware.rate_limit import RateLimitConfig

cors_config = CORSConfig(allow_origins=["*"])

load_dotenv()


async def rate_limit_exceeded_handler(request: Request, response: Response, pexpire: int):
    expire = ceil(pexpire / 1000)
    raise HTTPException(status_code=429, detail="Too Many Requests.", headers={"Retry-After": str(expire)})


async def custom_throttle_handler(request: Request):
    payload = await request.json()
    print(payload)
    client = request.client.host
    try:
        if payload.get("model").startswith("gpt-4"):
            with RateLimit(resource="users_list", client=client, max_requests=3, expire=60):
                return True
        elif payload.get("model").startswith("gpt-3.5-turbo"):
            with RateLimit(resource="users_list", client=client, max_requests=4, expire=60):
                return True
        else:
            with RateLimit(resource="users_list", client=client, max_requests=5, expire=60):
                return True
    except TooManyRequests:
        return False


rate_limit_config = RateLimitConfig(rate_limit=("minute", 1), check_throttle_handler=custom_throttle_handler)

# Loads the normal models
with open("data/models.json") as f:
    model_list = json.load(f)

# Loads the RP models
with open("data/modelsRP.json") as f:
    rp_model_list = json.load(f)

# Loads the keys
with open("data/keys.json") as keys:
    keylist = json.load(keys)

keys = keylist.get("keys")
models = [data["id"] for data in model_list["data"]]
rp_models = [data["id"] for data in rp_model_list["data"]]


# Function for tokenizing a sentence
def tokenize(text: str, model: str) -> tuple[int, list[int]]:
    encoding = tiktoken.encoding_for_model(model)
    encoded = encoding.encode(text)
    return len(encoded), encoded


# Function for getting a single normal model info
def get_model_info(id_value):
    return next((data for data in model_list["data"] if data["id"] == id_value), None)


# Function for getting a single model info
def get_rp_model_info(id_value):
    return next((data for data in rp_model_list["data"] if data["id"] == id_value), None)


# Function for checking if a key exists by a Discord ID
def check_id_key(id_value):
    return any(data["id"] == id_value for data in keylist["keys"])


# Function for checking if a key exists by its value
def check_key(key):
    return any(data["key"] == key for data in keylist["keys"])


# Routes
@litestar.route(sync_to_thread=True, path="/", http_method=["GET", "POST", "DELETE", "PATCH", "PUT"])
def root() -> dict[str, str]:
    """Returns the root response."""
    try:
        return {"detail": "The official VortexAI (HentAI) API!", "discord": "https://discord.gg/7WabGcsBsg"}
    except Exception as e:
        print(e)


@litestar.route(sync_to_thread=True, path="/v1", http_method=["GET", "POST", "DELETE", "PATCH", "PUT"])
def v1() -> dict[str, str]:
    """Returns the /v1 endpoint response."""
    return {"detail": "Go to /v1/chat/completions or /v1/models."}


@litestar.route(sync_to_thread=True, path="/rp", http_method=["GET", "POST", "DELETE", "PATCH", "PUT"])
def rp() -> dict[str, str]:
    """Returns the /v1 endpoint response."""
    return {"detail": "Go to /rp/chat/completions or /rp/models."}


@litestar.route(sync_to_thread=True, path="/v1/models", http_method=["GET", "POST", "DELETE", "PATCH", "PUT"])
def v1_models() -> None:
    """Returns the /v1/models endpoint response."""
    return model_list


@litestar.route(sync_to_thread=True, path="/rp/models", http_method=["GET", "POST", "DELETE", "PATCH", "PUT"])
def rp_models() -> None:
    """Returns the /rp/models endpoint response."""
    return rp_model_list


@litestar.route(
    sync_to_thread=True, path="/v1/models/{model:str}", http_method=["GET", "POST", "DELETE", "PATCH", "PUT"]
)
def v1_model_info(model: str) -> None:
    model_info = get_model_info(model)
    """Returns the /v1/models/%model% endpoint response."""
    return model_info if model_info is not None else {"error": "The specified model does not exist."}


@litestar.route(
    sync_to_thread=True,
    path="/supersecretadminkeylol/add-key/{id:str}",
    http_method=["GET", "POST", "DELETE", "PATCH", "PUT"],
)
def admin_add_key(id: str) -> dict[str, str]:
    key_gen = f"ht-{secrets.token_urlsafe(35)}"
    if key_check := check_id_key(id):
        """Returns that a key already exists for an ID."""
        return {"error": "The key for the specified ID already exists."}
    else:
        keys.append({"id": id, "key": key_gen})

        with open("data/keys.json", "w") as keysFile:
            json.dump(keylist, keysFile, ensure_ascii=False, indent=4)

        """Returns that the key was generated along side the key."""
        return {"success": "Successfully generated key.", "api_key": key_gen}


@litestar.route(
    sync_to_thread=True,
    path="/supersecretadminkeylol/check-key/{id:str}",
    http_method=["GET", "POST", "DELETE", "PATCH", "PUT"],
)
def admin_check_key(id: str) -> dict[str, str]:
    if key_check := check_id_key(id):
        for data in keylist["keys"]:
            if data["id"] == id:
                """Returns if a key is present."""
                return {"present": True, "api_key": data["key"]}

    else:
        """Returns if a key is not present."""
        return {"present": False}


@litestar.route(
    sync_to_thread=True,
    path="/supersecretadminkeylol/revoke-key/{id:str}",
    http_method=["GET", "POST", "DELETE", "PATCH", "PUT"],
)
def admin_revoke_key(id: str) -> dict[str, str]:
    if key_check := check_id_key(id):
        cooldown_info = next((info for info in keylist if info[0] == id), None)

        keys.remove({"id": id, "key": cooldown_info[1]})

        with open("data/keys.json", "w") as keysFile:
            json.dump(keylist, keysFile, ensure_ascii=False, indent=4)

        """Returns if the specified ID's key was deleted."""
        return {"success": "Successfully revoked key."}
    else:
        """Returns if a key does not exist for an ID."""
        return {"error": "The key for the specified ID does not exist."}


@litestar.post(sync_to_thread=True, path="/rp/chat/completions")
def rp_chat_completions(request: Request, data: dict) -> dict:
    return {"detail": "WIP."}
    # global stream
    #
    # start_time = time.time()
    #
    # model_request = data.get("model", "meta-llama/Llama-2-70b-chat-hf")
    # stream = data.get("streaming")
    # if stream is None:
    #     stream = data.get("stream")
    #     if stream is None:
    #         stream = False
    # messages = data.get("messages")
    #
    # if model_request not in rp_models:
    #     """Returns if a model does not exist."""
    #     return {"error": "The specified model does not exist."}
    #
    # try:
    #     request_key = request.headers.get('Authorization').split(' ')
    # except:
    #     """Returns if a key was not provided."""
    #     return {"error": "No API key was provided."}
    # try:
    #     check_key_header = check_key(request_key[1])
    #     if not check_key_header:
    #         """Returns if a key does not exist."""
    #         return {"error": "An invalid API key was provided."}
    #
    # except:
    #     """Returns if an error occurred while validating the API key."""
    #     return {"error": "An exception occurred while validating your API key."}
    #
    # try:
    #     response = openai.ChatCompletion.create(api_base=os.getenv("RP_API_BASE"),
    #                                             api_key="",
    #                                             model=model_request,
    #                                             stream=False,
    #                                             messages=messages)
    #     print(response)
    # except Exception as e:
    #     print(e)
    #     """Returns if an error occurred while generating the response with OpenAI."""
    #     return {"error": "An error occurred while generating the response."}
    #
    # completion_id = ''.join(
    #     random.choices(string.ascii_letters + string.digits, k=28))
    # completion_timestamp = int(time.time())
    #
    # if stream:
    #     json_data = {
    #         'id':
    #             f'chatcmpl-{completion_id}',
    #         'object':
    #             'chat.completion.chunk',
    #         'created':
    #             completion_timestamp,
    #         'model':
    #             model_request,
    #         'choices': [{
    #             'index': 0,
    #             'delta': {
    #                 'content': response['choices'][0]['delta']['content'],
    #             },
    #             'finish_reason': None,
    #         }],
    #     }
    #
    #     """Returns the streaming response."""
    #     return json_data
    #
    # if not stream:
    #     json_data = {
    #         'id':
    #             f'chatcmpl-{completion_id}',
    #         'object':
    #             'chat.completion',
    #         'created':
    #             completion_timestamp,
    #         'model':
    #             model_request,
    #         'choices': [{
    #             'index': 0,
    #             'message': {
    #                 'role': 'assistant',
    #                 'content': response['choices'][0]['delta']['content'],
    #             },
    #             'finish_reason': 'stop',
    #         }]
    #     }
    #
    #     """Returns the normal response."""
    #     return json_data


@litestar.post(sync_to_thread=True, path="/v1/chat/completions")
def v1_chat_completions(request: Request, data: dict) -> dict:
    global stream

    start_time = time.time()

    stream = data.get("stream")
    messages = data.get("messages")
    model = data.get("model")

    try:
        request_key = request.headers.get("Authorization").split(" ")
    except:
        """Returns if a key was not provided."""
        return {"error": "No API key was provided."}
    try:
        check_key_header = check_key(request_key[1])
        if not check_key_header:
            """Returns if a key does not exist."""
            return {"error": "An invalid API key was provided."}

    except:
        """Returns if an error occurred while validating the API key."""
        return {"error": "An exception occurred while validating your API key."}

    try:
        response = openai.ChatCompletion.create(
            api_base=os.getenv("API_BASE"), api_key=os.getenv("API_KEY"), model=model, stream=False, messages=messages
        )
    except Exception as e:
        print(e)
        """Returns if an error occurred while generating the response with OpenAI."""
        return {"error": "An error occurred while generating the response."}

    completion_id = "".join(random.choices(string.ascii_letters + string.digits, k=28))
    completion_timestamp = int(time.time())

    if stream:
        """Returns the streaming response."""
        return {
            "id": f"chatcmpl-{completion_id}",
            "object": "chat.completion.chunk",
            "created": completion_timestamp,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "content": response["choices"][0]["delta"]["content"],
                    },
                    "finish_reason": None,
                }
            ],
        }
    prompt_tokens, _ = tokenize(text=messages[0]["content"], model="gpt-4")
    completion_tokens, _ = tokenize(text=response["choices"][0]["delta"]["content"], model="gpt-4")

    json_data = {
        "id": f"chatcmpl-{completion_id}",
        "object": "chat.completion",
        "created": completion_timestamp,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response["choices"][0]["delta"]["content"],
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }

    """Returns the normal response."""
    return json_data


# Defines the app variable
app = litestar.Litestar(
    route_handlers=[
        root,
        v1,
        v1_models,
        v1_model_info,
        admin_add_key,
        admin_revoke_key,
        admin_check_key,
        v1_chat_completions,
        rp_chat_completions,
        rp_models,
        rp,
    ],
    middleware=[rate_limit_config.middleware],
    cors_config=cors_config,
    debug=True,
)

# Runs the app
uvicorn.run(host="localhost", port=1337, app=app, log_level="debug")
