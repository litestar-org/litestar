from pydantic import BaseModel


class Form(BaseModel):
    name: str
    age: int
    programmer: bool
    value: str
