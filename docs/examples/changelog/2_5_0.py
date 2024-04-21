class Foo:
    pass


@get()
def handler() -> None:
    raise ValidationException(extra={"foo": Foo("bar")})


app = Litestar(route_handlers=[handler], type_encoders={Foo: lambda foo: "foo"})