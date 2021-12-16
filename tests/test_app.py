from starlite import Starlite, get


def test_app_register():
    @get(path="/")
    def my_fn():
        pass

    app = Starlite()
    assert len(app.router.routes) == 1

    app.register(my_fn)
    assert len(app.router.routes) == 2
