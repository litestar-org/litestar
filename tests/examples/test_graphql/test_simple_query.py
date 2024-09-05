from collections.abc import Iterator

import pytest
from docs.examples.graphql import simple_query

from litestar import Litestar
from litestar.status_codes import HTTP_200_OK
from litestar.testing import TestClient


@pytest.fixture(scope="function")
def client() -> Iterator[TestClient[Litestar]]:
    with TestClient(app=simple_query.app) as client:
        yield client


@pytest.mark.parametrize(
    "query, expected_response",
    [
        (
            """
            query {
                movies {
                    title
                }
            }
            """,
            {
                "data": {
                    "movies": [
                        {"title": "The Silent Storm"},
                        {"title": "Whispers in the Wind"},
                        {"title": "Echoes of Tomorrow"},
                        {"title": "Fading Horizons"},
                        {"title": "Broken Dreams"},
                    ]
                }
            },
        )
    ],
)
def test_simple_query_get_titles(client: TestClient[Litestar], query: str, expected_response: str):
    response = client.get("/movies", params={"query": query.strip()}, headers={"content-type": "application/json"})
    assert response.status_code == HTTP_200_OK
    assert response.json() == expected_response


@pytest.mark.parametrize(
    "query, expected_response",
    [
        (
            """
            query {
                movies {
                    director
                }
            }
            """,
            {
                "data": {
                    "movies": [
                        {"director": "Ella Parker"},
                        {"director": "Daniel Brooks"},
                        {"director": "Sophia Rivera"},
                        {"director": "Lucas Mendes"},
                        {"director": "Amara Patel"},
                    ]
                }
            },
        )
    ],
)
def test_simple_query_get_directors(client: TestClient[Litestar], query: str, expected_response: dict):
    response = client.get("/movies", params={"query": query.strip()}, headers={"Content-Type": "application/json"})
    assert response.status_code == HTTP_200_OK
    assert response.json() == expected_response
