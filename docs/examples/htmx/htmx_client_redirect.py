from litestar import get
from litestar.contrib.htmx.response import ClientRedirect


@get("/")
def handler() -> ClientRedirect:
    return ClientRedirect(redirect_to="/contact-us")
