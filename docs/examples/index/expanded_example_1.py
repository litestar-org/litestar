from pydantic import BaseModel, UUID4


class User(BaseModel):
    first_name: str
    last_name: str
    id: UUID4