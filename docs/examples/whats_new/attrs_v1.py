from litestar import get
from litestar.params import Parameter


@get("/")
def index(param: int = Parameter(gt=5)) -> dict[str, int]: ...
