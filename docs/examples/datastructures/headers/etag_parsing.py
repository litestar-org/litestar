from litestar.datastructures import ETag

assert ETag.from_header('"foo"') == ETag(value="foo")
assert ETag.from_header('W/"foo"') == ETag(value="foo", weak=True)
