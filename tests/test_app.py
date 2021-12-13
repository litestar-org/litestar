from starlite import Starlite, get


def test_app_register():
    @get(path="/")
    def my_fn():
        pass

    app = Starlite()
    assert not app.router.routes

    app.register(my_fn)
    assert app.router.routes
