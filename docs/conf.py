import importlib.metadata
import os
import re
from functools import partial
from typing import Any

from sphinx.addnodes import document
from sphinx.application import Sphinx

__all__ = ["setup", "update_html_context"]


project = "Litestar"
copyright = "2023, Litestar-API"
author = "Litestar-API"
release = os.getenv("_LITESTAR_DOCS_BUILD_VERSION", importlib.metadata.version("litestar").rsplit(".")[0])

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

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "msgspec": ("https://jcristharif.com/msgspec/", None),
    "anyio": ("https://anyio.readthedocs.io/en/stable/", None),
    "multidict": ("https://multidict.aio-libs.org/en/stable/", None),
    "sqlalchemy": ("https://docs.sqlalchemy.org/en/20/", None),
    "click": ("https://click.palletsprojects.com/en/8.1.x/", None),
    "redis": ("https://redis-py.readthedocs.io/en/stable/", None),
    "picologging": ("https://microsoft.github.io/picologging", None),
    "structlog": ("https://www.structlog.org/en/stable/", None),
    "tortoise": ("https://tortoise.github.io/", None),
    "piccolo": ("https://piccolo-orm.readthedocs.io/en/latest", None),
    "opentelemetry": ("https://opentelemetry-python.readthedocs.io/en/latest/", None),
}


napoleon_google_docstring = True
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = False
napoleon_attr_annotations = True

autoclass_content = "class"
autodoc_class_signature = "separated"
autodoc_default_options = {"special-members": "__init__", "show-inheritance": True, "members": True}
autodoc_member_order = "bysource"
autodoc_typehints_format = "short"


nitpicky = True
nitpick_ignore = [
    # external library / undocumented external
    ("py:class", "BaseModel"),
    ("py:class", "pydantic.main.BaseModel"),
    ("py:class", "pydantic.generics.GenericModel"),
    ("py:class", "redis.asyncio.Redis"),
    ("py:class", "sqlalchemy.orm.decl_api.DeclarativeMeta"),
    ("py:class", "sqlalchemy.sql.sqltypes.TupleType"),
    ("py:class", "sqlalchemy.dialects.postgresql.named_types.ENUM"),
    # type vars and aliases / intentionally undocumented
    ("py:class", "RouteHandlerType"),
    ("py:obj", "litestar.security.base.AuthType"),
    ("py:class", "ControllerRouterHandler"),
    ("py:class", "PathParameterDefinition"),
    ("py:class", "BaseSessionBackendT"),
    ("py:class", "AnyIOBackend"),
    ("py:class", "T"),
    ("py:class", "C"),
    # intentionally undocumented
    ("py:class", "NoneType"),
    ("py:class", "litestar._signature.field.SignatureField"),
]
nitpick_ignore_regex = [
    (r"py:.*", r"litestar\.types.*"),
    (r"py:.*", r"litestar.*\.T"),
    (r"py:.*", r".*R_co"),
    (r"py:.*", r".*UserType"),
    (r"py:.*", r"litestar\.middleware\.session\.base\.BaseSessionBackendT"),
    (r"py:obj", r"typing\..*"),
    (r"py:.*", r"httpx.*"),
    # type vars
    ("py:.*", r"litestar\.pagination\.C"),
    ("py:.*", r"litestar.middleware.session.base.ConfigT"),
    ("py:.*", r"multidict\..*"),
    (r"py:.*", r"litestar\.connection\.base\.UserT"),
    (r"py:.*", r"litestar\.connection\.base\.AuthT"),
    (r"py:.*", r"litestar\.connection\.base\.StateT"),
    (r"py:.*", r"litestar\.connection\.base\.HandlerT"),
]

# Warnings about missing references to those targets in the specified location will be ignored.
# The source of the references is taken 1:1 from the warnings as reported by Sphinx, e.g
# **/litestar/testing/client/async_client.py:docstring of litestar.testing.AsyncTestClient.exit_stack:1: WARNING: py:class reference target not found: AsyncExitStack
# would be added as: "litestar.testing.AsyncTestClient.exit_stack": {"AsyncExitStack"},
ignore_missing_refs = {
    # No idea what autodoc is doing here. Possibly unfixable on our end
    "litestar.template.base.TemplateEngineProtocol.get_template": {"litestar.template.base.T_co"},
    "litestar.template": {"litestar.template.base.T_co"},
    "litestar.openapi.OpenAPIController.security": {"SecurityRequirement"},
    "litestar.contrib.sqlalchemy_1.plugin.SQLAlchemyPlugin.handle_string_type": {"BINARY", "VARBINARY", "LargeBinary"},
    "litestar.contrib.sqlalchemy_1.plugin.SQLAlchemyPlugin.is_plugin_supported_type": {"DeclarativeMeta"},
    re.compile(r"litestar\.plugins.*"): re.compile(".*(ModelT|DataContainerT)"),
    re.compile(r"litestar\.contrib\.sqlalchemy\.init_plugin\.config.*"): re.compile(
        ".*(ConnectionT|EngineT|SessionT|SessionMakerT)"
    ),
}


auto_pytabs_min_version = (3, 8)
auto_pytabs_max_version = (3, 11)
auto_pytabs_compat_mode = True

autosectionlabel_prefix_document = True

suppress_warnings = [
    "autosectionlabel.*",
    "ref.python",  # TODO: remove when https://github.com/sphinx-doc/sphinx/issues/4961 is fixed
]

html_theme = "litestar_sphinx_theme"
html_static_path = ["_static"]
html_js_files = ["versioning.js"]
html_css_files = ["style.css"]
html_show_sourcelink = False
html_title = "Litestar Framework"


html_theme_options = {
    "use_page_nav": False,
    "github_repo_name": "litestar",
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
            "Releases": "https://starliteproject.dev/about/litestar-releases",
        },
        "Release notes": {
            "2.0 migration guide": "release-notes/migration_guide_2",
            "2.x Changelog": "https://docs.starliteproject.dev/2/release-notes/changelog.html",
            "1.x Changelog": "https://docs.starliteproject.dev/1/release-notes/changelog.html",
        },
    },
}


def update_html_context(
    app: Sphinx, pagename: str, templatename: str, context: dict[str, Any], doctree: document
) -> None:
    context["generate_toctree_html"] = partial(context["generate_toctree_html"], startdepth=0)


def setup(app: Sphinx) -> dict[str, bool]:
    app.setup_extension("litestar_sphinx_theme")
    app.setup_extension("pydata_sphinx_theme")
    app.connect("html-page-context", update_html_context)

    return {"parallel_read_safe": True, "parallel_write_safe": True}
