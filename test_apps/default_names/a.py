from litestar import get, Request


@get("/a")
def func(request: Request) -> None:
    # a.func
    path = request.app.route_reverse("test_apps.default_names.a.func", user_id=100, group_id=10)

    pass
