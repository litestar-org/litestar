from litestar import Litestar

from my_app.controllers.user import UserController

app = Litestar(route_handlers=[UserController])