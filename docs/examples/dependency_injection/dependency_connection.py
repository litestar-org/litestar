from litestar.testing import TestClient
from dependencies import app, CONNECTION

with TestClient(app=app) as client:
    print(client.get("/").json())  # {"open": True}
    print(CONNECTION)  # {"open": False}