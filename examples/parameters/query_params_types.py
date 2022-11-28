from datetime import datetime, timedelta
from typing import Any, Dict

from starlite import Starlite, get


@get("/")
def index(
    date: datetime,
    number: int,
    floating_number: float,
    strings: list[str],
) -> Dict[str, Any]:
    return {
        "datetime": date + timedelta(days=1),
        "int": number,
        "float": floating_number,
        "list": strings,
    }


app = Starlite(route_handlers=[index])
