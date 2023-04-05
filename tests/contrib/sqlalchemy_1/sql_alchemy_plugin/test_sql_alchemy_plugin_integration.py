from typing import List

from polyfactory.value_generators.primitives import (
    create_random_float,
    create_random_string,
)

from starlite import get, post
from starlite.contrib.sqlalchemy_1.plugin import SQLAlchemyPlugin
from starlite.status_codes import HTTP_200_OK, HTTP_201_CREATED
from starlite.testing import create_test_client
from tests.contrib.sqlalchemy_1.sql_alchemy_plugin.models import Company

companies = [
    Company(id=i, name=create_random_string(min_length=5, max_length=20), worth=create_random_float(minimum=1))
    for i in range(3)
]


@get(path="/companies/{company_id:int}")
def get_company_by_id(company_id: int) -> Company:
    return list(filter(lambda x: x.id == company_id, companies))[0]


@get(path="/companies")
def get_companies() -> List[Company]:
    return companies


@post(path="/companies")
def create_company(data: Company) -> Company:
    assert isinstance(data, Company)
    return data


@post(path="/companies/bulk")
def bulk_create_company(data: List[Company]) -> List[Company]:
    assert all(isinstance(datum, Company) for datum in data)
    return data


def test_return_single_sql_alchemy_model_instances() -> None:
    with create_test_client([get_companies], plugins=[SQLAlchemyPlugin()]) as client:
        response = client.get("/companies")
        assert response.status_code == HTTP_200_OK
        assert response.json() == [
            {"id": company.id, "name": company.name, "worth": company.worth} for company in companies
        ]


def test_return_of_a_single_sql_alchemy_model_instance() -> None:
    with create_test_client([get_company_by_id], plugins=[SQLAlchemyPlugin()]) as client:
        response = client.get("/companies/1")
        assert response.status_code == HTTP_200_OK
        assert (
            response.json()
            == [
                {"id": company.id, "name": company.name, "worth": company.worth}
                for company in list(filter(lambda x: x.id == 1, companies))
            ][0]
        )


def test_serializing_a_single_sql_alchemy_instance() -> None:
    company = {"id": 10, "name": create_random_string(), "worth": create_random_float()}
    with create_test_client([create_company], plugins=[SQLAlchemyPlugin()]) as client:
        response = client.post("/companies", json=company)
        assert response.status_code == HTTP_201_CREATED
        assert response.json() == company


def test_serializing_a_list_of_sql_alchemy_instances() -> None:
    serialized_companies = [{"id": company.id, "name": company.name, "worth": company.worth} for company in companies]
    with create_test_client([bulk_create_company], plugins=[SQLAlchemyPlugin()]) as client:
        response = client.post("/companies/bulk", json=serialized_companies)
        assert response.status_code == HTTP_201_CREATED
        assert response.json() == serialized_companies
