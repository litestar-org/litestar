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


app = Litestar(route_handlers=[show_user_profile, show_post, show_subpath])
