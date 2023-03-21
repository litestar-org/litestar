from __future__ import annotations

import importlib.metadata
import os
from functools import partial
from typing import Any, TYPE_CHECKING


if TYPE_CHECKING:
    from sphinx.addnodes import document
    from sphinx.application import Sphinx


project = "Starlite"
copyright = "2023, Starlite-API"
author = "Starlite-API"
release = os.getenv("_STARLITE_DOCS_BUILD_VERSION", importlib.metadata.version("starlite").rsplit(".")[0])

extensions = [
    "sphinx.ext.intersphinx",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_design",
    "auto_pytabs.sphinx_ext",
    "tools.sphinx_ext",
    "sphinx_copybutton",
    "sphinxcontrib.mermaid",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "msgspec": ("https://jcristharif.com/msgspec/", None),
    "anyio": ("https://anyio.readthedocs.io/en/stable/", None),
    "multidict": ("https://multidict.aio-libs.org/en/stable/", None),
    "sqlalchemy": ("https://docs.sqlalchemy.org/en/14/", None),
}


napoleon_google_docstring = True
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = False
napoleon_attr_annotations = True

autoclass_content = "class"
autodoc_class_signature = "separated"
autodoc_default_options = {
    "special-members": "__init__",
    "show-inheritance": True,
}
autodoc_member_order = "bysource"
autodoc_typehints_format = "short"

auto_pytabs_min_version = (3, 8)
auto_pytabs_max_version = (3, 11)

autosectionlabel_prefix_document = True

suppress_warnings = ["autosectionlabel.*"]

html_theme = "starlite_sphinx_theme"
html_static_path = ["_static"]
html_js_files = ["versioning.js"]
html_show_sourcelink = False
html_title = "Starlite Framework"


html_theme_options = {
    "use_page_nav": False,
    "github_repo_name": "starlite",
    "logo": {
        "link": "https://starliteproject.dev",
    },
    "extra_navbar_items": {
        "Documentation": "index",
        "Community": {
            "Contribution Guide": "contribution-guide",
            "Code of Conduct": "https://github.com/starlite-api/.github/blob/main/CODE_OF_CONDUCT.md",
        },
        "About": {
            "Organization": "https://starliteproject.dev/about/organization",
            "Releases": "https://starliteproject.dev/about/starlite-releases",
        },
        "Release notes": {
            "1.x Changelog": "https://docs.starliteproject.dev/1/changelog.html",
        },
    },
}


def update_html_context(
    app: Sphinx, pagename: str, templatename: str, context: dict[str, Any], doctree: document
) -> None:
    context["generate_toctree_html"] = partial(context["generate_toctree_html"], startdepth=0)


def setup(app: Sphinx) -> dict[str, bool]:
    app.connect("html-page-context", update_html_context, priority=1000)

    return {"parallel_read_safe": True, "parallel_write_safe": True}
