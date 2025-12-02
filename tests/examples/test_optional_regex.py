from docs.examples.lifecycle_hooks.after_request import app as after_request_app
from docs.examples.lifecycle_hooks.after_response import app as after_response_app
from docs.examples.lifecycle_hooks.before_request import app as before_request_app
from docs.examples.lifecycle_hooks.layered_hooks import app as layered_hooks_app

from litestar.testing import TestClient

from typing import Annotated, Optional
import msgspec
from msgspec import Meta

URL = Annotated[
    str,
    Meta(pattern=r"(https?:\/\/)..."),
]

class Base(msgspec.Struct):
    url: Optional[URL] = None

# This SHOULD fail but currently passes
POST / {"url": "htp:/gogle.com"} 


# this should work 
POST / {"url": "https://google.com"}

# before and after 201 
POST / {"url": null}

# before and after fix should still return 400
POST / {"url": "htp:/gogle.com"}  # When URL is required, not Optional