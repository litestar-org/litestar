from enum import Enum

from litestar.exceptions import HTTPException


class PetException(HTTPException):
    status_code = 406


class Gender(str, Enum):
    MALE = "M"
    FEMALE = "F"
    OTHER = "O"
    ANY = "A"
