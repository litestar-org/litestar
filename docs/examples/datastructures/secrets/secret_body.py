from dataclasses import dataclass

from litestar import post
from litestar.datastructures.secret_values import SecretString
from litestar.params import JSONBody


@dataclass
class Sensitive:
    value: SecretString


@post(sync_to_thread=False)
def post_handler(data: JSONBody[Sensitive]) -> Sensitive:
    return data
