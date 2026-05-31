from typing import Dict

from litestar import Litestar, Router, get
from litestar.di import NamedDependency


class PaymentService:
    def charge(self, amount: int) -> str:
        return f"charged {amount}"


async def provide_payments() -> PaymentService:
    return PaymentService()


async def provide_current_user_id() -> int:
    return 42


@get("/charge")
async def charge_handler(payments: NamedDependency[PaymentService], user_id: int) -> Dict[str, object]:
    return {"user_id": user_id, "result": payments.charge(100)}


router = Router(
    path="/api",
    route_handlers=[charge_handler],
    dependencies={"user_id": provide_current_user_id},
)

app = Litestar(
    route_handlers=[router],
    dependencies={"payments": provide_payments},
)
