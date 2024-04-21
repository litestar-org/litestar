@post(path="/", sync_to_thread=False)
def test(data: str = "abc") -> dict:
    return {"foo": data}