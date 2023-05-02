import importlib.metadata
import os
import re
from functools import partial
from typing import Any

from sphinx.addnodes import document
from sphinx.application import Sphinx

__all__ = ["setup", "update_html_context"]


project = "Litestar"
copyright = "2023, Litestar-Org"
author = "Litestar-Org"
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
    ("py:class", "_orm.Mapper"),
    ("py:class", "_orm.registry"),
    ("py:class", "_schema.MetaData"),
    ("py:class", "_schema.Table"),
    ("py:class", "_RegistryType"),
    ("py:class", "abc.Collection"),
    ("py:class", "TypeEngine"),
    ("py:class", "ExternalType"),
    ("py:class", "UserDefinedType"),
    ("py:class", "_types.TypeDecorator"),
    ("py:meth", "_types.TypeDecorator.process_bind_param"),
    ("py:meth", "_types.TypeDecorator.process_result_value"),
    ("py:meth", "type_engine"),
    # type vars and aliases / intentionally undocumented
    ("py:class", "RouteHandlerType"),
    ("py:obj", "litestar.security.base.AuthType"),
    ("py:class", "ControllerRouterHandler"),
    ("py:class", "PathParameterDefinition"),
    ("py:class", "BaseSessionBackendT"),
    ("py:class", "litestar.contrib.repository.abc.CollectionT"),
    ("py:class", "litestar.contrib.sqlalchemy.repository.SelectT"),
    ("py:class", "AnyIOBackend"),
    ("py:class", "T"),
    ("py:class", "C"),
    ("py:class", "EmptyType"),
    # intentionally undocumented
    ("py:class", "NoneType"),
    ("py:class", "litestar._signature.field.SignatureField"),
    ("py:class", "litestar.utils.signature.ParsedType"),
    ("py:class", "litestar.utils.signature.ParsedSignature"),
    ("py:class", "litestar.utils.signature.ParsedParameter"),
    ("py:class", "litestar.utils.sync.AsyncCallable"),
]
nitpick_ignore_regex = [
    (r"py:.*", r"litestar\.types.*"),
    (r"py:.*", r"litestar.*\.T"),
    (r"py:.*", r".*R_co"),
    (r"py:.*", r"ModelT"),
    (r"py:.*", r"litestar.contrib.sqlalchemy.repository.ModelT"),
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
    re.compile(r"litestar\.plugins.*"): re.compile(".*ModelT"),
    re.compile(r"litestar\.contrib\.sqlalchemy\.*"): re.compile(
        ".*(ConnectionT|EngineT|SessionT|SessionMakerT|SlotsBase|DataT)"
    ),
    re.compile(r"litestar\.dto.*"): re.compile(".*DataT|.*ParsedType"),
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
        "link": "https://litestar.dev",
    },
    "extra_navbar_items": {
        "Documentation": "index",
        "Community": {
            "Contributing": {
                "description": "Learn how to contribute to the Litestar project",
                "link": "https://docs.litestar.dev/2/contribution-guide.html",
                "icon": "contributing",
            },
            "Code of Conduct": {
                "description": "Review the etiquette for interacting with the Litestar community",
                "link": "https://github.com/litestar-org/.github/blob/main/CODE_OF_CONDUCT.md",
                "icon": "coc",
            },
        },
        "About": {
            "Litestar Organization": {
                "description": "Details about the Litestar organization",
                "link": "about/organization",
                "icon": "org",
            },
            "Releases": {
                "description": "Details about the Litestar release process",
                "link": "about/litestar-releases",
                "icon": "releases",
            },
        },
        "Release notes": {
            "2.0 migration guide": "release-notes/migration_guide_2",
            "2.x Changelog": "https://docs.litestar.dev/2/release-notes/changelog.html",
            "1.x Changelog": "https://docs.litestar.dev/1/release-notes/changelog.html",
        },
        "Help": "https://github.com/orgs/litestar-org/discussions",
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
