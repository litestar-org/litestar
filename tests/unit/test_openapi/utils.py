from enum import Enum, StrEnum

from litestar.exceptions import HTTPException


class PetException(HTTPException):
    status_code = 406


class Gender(StrEnum):
    """Docstring description"""

    MALE = "M"
    FEMALE = "F"
    OTHER = "O"
    ANY = "A"


class LuckyNumber(int, Enum):
    TWO = 2
    SEVEN = 7
