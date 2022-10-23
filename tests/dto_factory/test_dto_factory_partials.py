from starlite import DTOFactory
from starlite.plugins.sql_alchemy import SQLAlchemyPlugin
from starlite.types.partial import Partial

from tests import Person, Car
from tests.plugins.sql_alchemy_plugin import Pet

dto_factory = DTOFactory(plugins=[SQLAlchemyPlugin()])


def test_partial_dto_pydantic():
    dto_person = dto_factory("dto_person", Person)
    dto_partial_person = Partial[Person]
    bob = dto_partial_person(first_name="Bob")
    assert bob.first_name == "Bob"


def test_partial_dto_sqlalchemy_model():
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
    assert ferrari.year == 2022

    # Test for partial DTO
    partial_dto_car = Partial[dto_car]
    ford = partial_dto_car(**car_two)
    assert ford.make == "Ford"
