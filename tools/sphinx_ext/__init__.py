from __future__ import annotations

from typing import TYPE_CHECKING

from . import missing_references, run_examples

if TYPE_CHECKING:
    from sphinx.application import Sphinx


def setup(app: Sphinx) -> dict[str, bool]:
    ext_config = {}
    ext_config.update(run_examples.setup(app))
    ext_config.update(missing_references.setup(app))

    return ext_config
