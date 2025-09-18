from enum import Enum

from litestar.exceptions import HTTPException


class PetException(HTTPException):
    status_code = 406


class Gender(str, Enum):
    """Docstring description"""

    MALE = "M"
    FEMALE = "F"
    OTHER = "O"
    ANY = "A"


class LuckyNumber(int, Enum):
    TWO = 2
    SEVEN = 7
