from dataclasses import dataclass

from litestar import Litestar, post
from litestar.plugins.problem_details import ProblemDetailsConfig, ProblemDetailsException, ProblemDetailsPlugin


@dataclass
class PurchaseItem:
    item_id: int
    quantity: int


@post("/purchase")
async def purchase(data: PurchaseItem) -> None:
    # Logic to check if the user has enough credit to buy the item.
    # We assume the user does not have enough credit.

    raise ProblemDetailsException(
        type_="https://example.com/probs/out-of-credit",
        title="You do not have enough credit.",
        detail="Your current balance is 30, but that costs 50.",
        instance="/account/12345/msgs/abc",
        extra={"balance": 30},
    )


problem_details_plugin = ProblemDetailsPlugin(ProblemDetailsConfig())
app = Litestar(route_handlers=[purchase], plugins=[problem_details_plugin])

# run: /purchase --header "Content-Type: application/json" --request POST --data '{"item_id": 1234, "quantity": 2}'
