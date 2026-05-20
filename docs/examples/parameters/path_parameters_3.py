import dataclasses
from typing import Any, Dict

from typing_extensions import Annotated

from litestar import Litestar, get
from litestar.openapi.spec.example import Example
from litestar.openapi.spec.external_documentation import ExternalDocumentation
from litestar.params import PathParameter


@dataclasses.dataclass
class Version:
    id: int
    specs: Dict[str, Any]


VERSIONS = {1: Version(id=1, specs={"some": "value"})}


@get(path="/versions/{version:int}", sync_to_thread=False)
def get_product_version(
    version: Annotated[
        int,
        PathParameter(
            title="Available Product Versions",
            description="Get a specific version spec from the available specs",
            examples=[Example(value=1)],
            external_docs=ExternalDocumentation(
                url="https://mywebsite.com/documentation/product#versions",  # type: ignore[arg-type]
            ),
        ),
    ],
) -> Version:
    return VERSIONS[version]


app = Litestar(route_handlers=[get_product_version])
