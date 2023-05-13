from uuid import UUID, uuid4

from pydantic import BaseModel

from litestar import Litestar, get


class IdModel(BaseModel):
    __schema_name__ = "IdContainer"

    id: UUID


@get("/id", sync_to_thread=False)
def retrieve_id_handler() -> IdModel:
    """

    Returns: An IdModel

    """
    return IdModel(id=uuid4())


app = Litestar(route_handlers=[retrieve_id_handler])
