from starlite import MediaType, Request, Response, Starlite, get


@get("/resource")
def retrieve_resource(request: Request) -> Response[bytes]:
    provided_types = [MediaType.TEXT, MediaType.HTML, "application/xml"]
    preferred_type = request.accept.best_match(provided_types, default=MediaType.TEXT)

    if preferred_type == MediaType.TEXT:
        content = b"Hello World!"
    elif preferred_type == MediaType.HTML:
        content = b"<h1>Hello World!</h1>"
    elif preferred_type == "application/xml":
        content = b"<xml><msg>Hello World!</msg></xml>"
    return Response(content=content, media_type=preferred_type)


app = Starlite(route_handlers=[retrieve_resource])

# run: /resource
# run: /resource -H "Accept: text/html"
# run: /resource -H "Accept: application/xml"
