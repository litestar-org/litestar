from starlite.contrib.sqlalchemy_1.plugin import SQLAlchemyPlugin
from starlite.dto import DTOFactory
from starlite.partial import Partial
from tests import Car, Person

dto_factory = DTOFactory(plugins=[SQLAlchemyPlugin()])


def test_partial_dto_pydantic() -> None:
    dto_partial_person = Partial[Person]
    bob = dto_partial_person(first_name="Bob")  # type: ignore
    assert bob.first_name == "Bob"  # type: ignore


def test_partial_dto_sqlalchemy_model() -> None:
    car_one = {
        "id": 1,
        "year": 2022,
        "make": "Ferrari",
        "model": "488 Challenge Evo",
        "horsepower": 670,
        "color_codes": {
            "red": "Rosso corsa",
            "black": "Nero",
            "yellow": "Giallo Modena",
        },
    }

    car_two = {
        "id": 2,
        "year": 1969,
        "make": "Ford",
        "model": "GT40",
        "horsepower": 380,
    }

    # Test for non-partial DTO
    dto_car = dto_factory("dto_cars", Car)
    ferrari = dto_car(**car_one)
    assert ferrari.year == 2022  # type: ignore

    # Test for partial DTO
    partial_dto_car = Partial[dto_car]  # type: ignore
    ford = partial_dto_car(**car_two)  # pyright: ignore
    assert ford.make == "Ford"  # type: ignore
