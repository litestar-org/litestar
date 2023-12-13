from litestar import Controller, get


class C(Controller):
    path = "/controller"

    @get("/c")
    def func(self) -> None:
        pass
        # c.C.func
