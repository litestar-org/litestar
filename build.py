from typing import Any, Dict

from setuptools_rust import Binding, RustExtension


def build(setup_kwargs: Dict[str, Any]) -> None:
    """
    Add rust_extensions to the setup dict
    """
    setup_kwargs["rust_extensions"] = [
        RustExtension("starlite.rust_backend", path="starlite/extensions/rust/Cargo.toml", binding=Binding.PyO3)
    ]


if __name__ == "__main__":
    build({})
