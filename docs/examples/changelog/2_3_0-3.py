from litestar import Litestar, Request, Response


class CustomException(Exception): ...


def handle_exc(req: Request, exc: CustomException) -> Response: ...