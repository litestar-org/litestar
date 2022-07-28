from typing import Any, Dict

from setuptools_rust import RustExtension


def build(setup_kwargs: Dict[str, Any]) -> None:
    """
    Add rust_extensions to the setup dict
    """
    setup_kwargs.update(
        rust_extensions=[RustExtension("starlite.route_map", path="./Cargo.toml", debug=False)], zip_safe=False
    )


if __name__ == "__main__":
    build({})
