import importlib.metadata
import os

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
    "click": ("https://click.palletsprojects.com/en/8.1.x/", None),
    "redis": ("https://redis-py.readthedocs.io/en/stable/", None),
    "pydantic_openapi_schema": ("https://starlite-api.github.io/pydantic-openapi-schema/", None),
    "picologging": ("https://microsoft.github.io/picologging", None),
    "structlog": ("https://www.structlog.org/en/stable/", None),
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
    ("py:class", "AnyIOBackend"),
    ("py:class", "T"),
    ("py:class", "C"),
    ("py:class", "BaseModel"),
    ("py:class", "pydantic.main.BaseModel"),
    ("py:class", "pydantic.generics.GenericModel"),
    ("py:class", "redis.asyncio.Redis"),
    # type vars
    ("py:class", "RouteHandlerType"),
    ("py:obj", "starlite.security.base.AuthType"),
    ("py:class", "ControllerRouterHandler"),
    ("py:class", "PathParameterDefinition"),
    ("py:class", "BaseSessionBackendT"),
    # intentionally undocumented
    ("py:class", "NoneType"),
    ("py:class", "starlite._signature.models.SignatureField"),
]
nitpick_ignore_regex = [
    (r"py:.*", r"starlite\.types.*"),
    (r"py:.*", r"starlite.*\.T"),
    (r"py:.*", r".*R_co"),
    (r"py:.*", r"starlite\.security\.base\.UserType"),
    (r"py:.*", r"starlite\.middleware\.session\.base\.BaseSessionBackendT"),
    (r"py:obj", r"typing\..*"),
    (r"py:.*", r"httpx.*"),
    # type vars
    ("py:.*", r"starlite\.plugins\.ModelT"),
    ("py:.*", r"starlite\.plugins\.DataContainerT"),
    ("py:.*", r"starlite\.pagination\.C"),
    ("py:.*", r"starlite.middleware.session.base.ConfigT"),
    ("py:.*", r"multidict\..*"),
]

# Warnings about missing references to those targets in the specified location will be ignored.
# The source of the references is taken 1:1 from the warnings as reported by Sphinx, e.g
# **/starlite/testing/client/async_client.py:docstring of starlite.testing.AsyncTestClient.exit_stack:1: WARNING: py:class reference target not found: AsyncExitStack
# would be added as: "starlite.testing.AsyncTestClient.exit_stack": {"AsyncExitStack"},
ignore_missing_refs = {
    # No idea what autodoc is doing here. Possibly unfixable on our end
    "starlite.template.base.TemplateEngineProtocol.get_template": {"starlite.template.base.T_co"},
    "starlite.template": {"starlite.template.base.T_co"},
    "starlite.openapi.OpenAPIController.security": {"SecurityRequirement"},
}

auto_pytabs_min_version = (3, 8)
auto_pytabs_max_version = (3, 11)
auto_pytabs_compat_mode = True

autosectionlabel_prefix_document = True

suppress_warnings = ["autosectionlabel.*"]

html_theme = "pydata_sphinx_theme"
html_static_path = ["_static"]
html_css_files = ["style.css"]
html_js_files = ["versioning.js"]
html_favicon = "images/favicon.ico"
html_logo = "images/logo.svg"
html_show_sourcelink = False
html_sidebars = {"about/*": []}
html_title = "Starlite Framework"

html_additional_pages = {"index": "landing-page.html"}


html_theme_options = {
    "use_edit_page_button": False,
    "show_toc_level": 4,
    "navbar_align": "left",
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/starlite-api/starlite",
            "icon": "fa-brands fa-github",
            "type": "fontawesome",
        },
        {
            "name": "Discord",
            "url": "https://discord.gg/X3FJqy8d2j",
            "icon": "fa-brands fa-discord",
            "type": "fontawesome",
        },
    ],
    "navbar_end": ["navbar-icon-links"],
    "navbar_persistent": ["search-button", "theme-switcher"],
}


html_context = {
    "navbar_items": {
        "Documentation": "lib/index",
        "Community": {
            "Contribution guide": "community/contribution-guide/index",
            "Code of Conduct": "https://github.com/starlite-api/.github/blob/main/CODE_OF_CONDUCT.md",
        },
        "About": {
            "Organization": "about/organization",
            "Releases": "about/starlite-releases",
        },
        "Release notes": "release-notes/index",
    }
}
