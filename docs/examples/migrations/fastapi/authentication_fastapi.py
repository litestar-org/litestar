from fastapi import FastAPI, Depends, Request


async def authenticate(request: Request) -> None: ...


app = FastAPI()


@app.get("/", dependencies=[Depends(authenticate)])
async def index() -> dict[str, str]: ...