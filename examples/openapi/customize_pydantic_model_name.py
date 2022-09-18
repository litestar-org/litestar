from uuid import UUID, uuid4

from pydantic import BaseModel

from starlite import Starlite, get


class IdModel(BaseModel):
    __schema_name__ = "IdContainer"

    id: UUID


@get("/id")
def retrieve_id_handler() -> IdModel:
    """

    Returns: An IdModel

    """
    return IdModel(id=uuid4())


app = Starlite(route_handlers=[retrieve_id_handler])
