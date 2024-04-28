from litestar import Litestar


def on_startup(app: Litestar) -> None:
    print(app.state.something)
