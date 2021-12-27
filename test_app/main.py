from starlite import MediaType, OpenAPIConfig, OpenAPIController, Starlite, get


@get(path="/", media_type=MediaType.TEXT)
def heath_check() -> str:
    return "healthy"


app = Starlite(route_handlers=[heath_check, OpenAPIController], openapi_config=OpenAPIConfig())
