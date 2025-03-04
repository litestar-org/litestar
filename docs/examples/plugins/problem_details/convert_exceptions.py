from __future__ import annotations

from dataclasses import dataclass

from litestar import Litestar, post
from litestar.plugins.problem_details import ProblemDetailsConfig, ProblemDetailsException, ProblemDetailsPlugin


@dataclass
class PurchaseItem:
    item_id: int
    quantity: int


class PurchaseNotAllowedError(Exception):
    def __init__(self, account_id: int, balance: int, detail: str) -> None:
        self.account_id = account_id
        self.balance = balance
        self.detail = detail


@post("/purchase")
async def purchase(data: PurchaseItem) -> None:
    raise PurchaseNotAllowedError(
        account_id=12345,
        balance=30,
        detail="Your current balance is 30, but that costs 50.",
    )


def convert_purchase_not_allowed_to_problem_details(exc: PurchaseNotAllowedError) -> ProblemDetailsException:
    return ProblemDetailsException(
        type_="https://example.com/probs/out-of-credit",
        title="You do not have enough credit.",
        detail=exc.detail,
        instance=f"/account/{exc.account_id}/msgs/abc",
        extra={"balance": exc.balance},
    )


problem_details_plugin = ProblemDetailsPlugin(
    ProblemDetailsConfig(
        enable_for_all_http_exceptions=True,
        exception_to_problem_detail_map={PurchaseNotAllowedError: convert_purchase_not_allowed_to_problem_details},
    )
)
app = Litestar(route_handlers=[purchase], plugins=[problem_details_plugin])

# run: /purchase --header "Content-Type: application/json" --request POST --data '{"item_id": 1234, "quantity": 2}'
