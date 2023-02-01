import asyncio
from typing import Any, Dict, Generator, TYPE_CHECKING
from unittest import mock

import pytest
from sqlalchemy.engine.result import ScalarResult
from sqlalchemy.ext.asyncio import AsyncSession

from .sqla_basic_app import Company, CompanyController
from starlite import Provide, Starlite
from starlite.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from starlite.testing import AsyncTestClient

if TYPE_CHECKING:
    from asyncio.events import AbstractEventLoop

    from pytest import FixtureRequest


class TestWithSqlalchemy:
    # Mock AsyncSession. This will be injected as a dependency whose methods will be patched particular to the test
    # case.
    async_session_mock = mock.MagicMock(AsyncSession)

    # The default scope of event loop is function. This fixture is created to set its scope to session.
    @pytest.fixture(scope="session")
    def event_loop(self) -> "AbstractEventLoop":
        return asyncio.get_event_loop()

    @pytest.fixture(scope="session")
    def app(self) -> Starlite:
        return Starlite(
            route_handlers=[CompanyController], dependencies={"async_session": Provide(lambda: self.async_session_mock)}
        )

    @pytest.fixture(scope="session")
    async def async_test_client(self, app: Starlite) -> Generator[AsyncTestClient, None, None]:
        async with AsyncTestClient(app=app) as client:
            yield client

    @pytest.fixture(autouse=True)
    def auto_configure_async_session_mock(self, request: "FixtureRequest") -> Generator[None, None, None]:
        """Automatically configures 'return_value' of the methods of 'AsyncSession' and resets them after each test."""
        # The 'return_value' of 'AsyncSession.scalars' is set by default. You can set your own by parameterizing this
        # fixture.
        mockers: Dict[str:Any] = getattr(request, "param", None) or {
            "scalars.return_value": mock.create_autospec(ScalarResult, instance=True)
        }
        self.async_session_mock.configure_mock(**mockers)
        yield
        # Reset the mock after each test so that patching that was done for the earlier test does not affect the next
        # test in execution.
        self.async_session_mock.reset_mock(return_value=True, side_effect=True)

    async def test_get_company_by_id(self, async_test_client: AsyncTestClient) -> None:
        """Should return a company whose ID exists in the database."""
        company = Company(id="12345", name="starlite-api")
        # This route handler uses "sqlalchemy.engine.result.ScalarResult.one_or_none" to retrieve the selected row so
        # patch the return_value of ".one_or_none" method.
        self.async_session_mock.configure_mock(**{"scalars.return_value.one_or_none.return_value": company})
        response = await async_test_client.get("/companies/12345")

        assert response.status_code == HTTP_200_OK
        assert response.json()["name"] == company.name

    async def test_get_companies_by_id_should_raise_exception_if_not_found(
        self, async_test_client: AsyncTestClient
    ) -> None:
        company_id = "54321"
        self.async_session_mock.configure_mock(**{"scalars.return_value.one_or_none.return_value": None})
        response = await async_test_client.get(f"/companies/{company_id}")

        assert response.status_code == HTTP_404_NOT_FOUND
        assert response.json()["detail"] == f"Company with ID {company_id} not found"

    @pytest.mark.parametrize(
        "companies",
        [
            [
                Company(id=_id, name=name)
                for _id, name in zip(("123", "456", "789"), ("starlite-api", "my company", "test company"))
            ],
            [],
        ],
    )
    async def test_get_all_companies(self, companies, async_test_client: AsyncTestClient) -> None:
        # This route handler uses "sqlalchemy.engine.result.ScalarResult.all" to retrieve all rows so patch the
        # return_value of ".all" method.
        self.async_session_mock.configure_mock(**{"scalars.return_value.all.return_value": companies})
        response = await async_test_client.get("/companies")

        assert response.status_code == HTTP_200_OK
        assert response.json() == [{"name": company.name} for company in companies]
