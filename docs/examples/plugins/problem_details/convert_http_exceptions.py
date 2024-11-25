from dataclasses import dataclass

from litestar import Litestar, post
from litestar.exceptions.http_exceptions import NotFoundException
from litestar.plugins.problem_details import ProblemDetailsConfig, ProblemDetailsPlugin


@dataclass
class PurchaseItem:
    item_id: int
    quantity: int


@post("/purchase")
async def purchase(data: PurchaseItem) -> None:
    # Logic to check if the user has enough credit to buy the item.
    # We assume the user does not have enough credit.

    raise NotFoundException(detail="No item with the given ID was found", extra={"item_id": data.item_id})


problem_details_plugin = ProblemDetailsPlugin(ProblemDetailsConfig(enable_for_all_http_exceptions=True))
app = Litestar(route_handlers=[purchase], plugins=[problem_details_plugin])

# run: /purchase --header "Content-Type: application/json" --request POST --data '{"item_id": 1234, "quantity": 2}'
