from litestar import get


@get("/")
def index(param: Annotated[int, Parameter(gt=5)]) -> dict[str, int]: ...
