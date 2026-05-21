import pathlib

from litestar import Litestar, get
from litestar.params import FromPath


@get("/user/{username:str}", sync_to_thread=False)
def show_user_profile(username: FromPath[str]) -> str:
    return f"User {username}"


@get("/post/{post_id:int}", sync_to_thread=False)
def show_post(post_id: FromPath[int]) -> str:
    return f"Post {post_id}"


@get("/path/{subpath:path}", sync_to_thread=False)
def show_subpath(subpath: FromPath[pathlib.Path]) -> str:
    return f"Subpath {subpath}"


app = Litestar([show_user_profile, show_post, show_subpath])

from litestar.status_codes import HTTP_200_OK
from litestar.testing import TestClient


def test_show_user_profile() -> None:
    with TestClient(app) as client:
        response = client.get("/user/julien")
        assert response.status_code == HTTP_200_OK
        assert response.text == "User julien"


def test_show_post() -> None:
    with TestClient(app) as client:
        response = client.get("/post/42")
        assert response.status_code == HTTP_200_OK
        assert response.text == "Post 42"


def test_show_subpath() -> None:
    with TestClient(app) as client:
        response = client.get("/path/a/b/c")
        assert response.status_code == HTTP_200_OK
        assert response.text == "Subpath /a/b/c"
