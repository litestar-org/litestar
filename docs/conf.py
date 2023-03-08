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
    ("py:class", "httpx.Client"),
    ("py:class", "httpx.AsyncClient"),
    ("py:class", "BaseModel"),
    ("py:class", "redis.asyncio.Redis"),
    # internal types we don't document intentionally
    ("py:class", "RouteHandlerType"),
    ("py:obj", "starlite.security.base.AuthType"),
    ("py:class", "ControllerRouterHandler"),
    # autodoc cannot link those in type hints for... reasons
    ("py:class", "AfterRequestHookHandler"),
    ("py:class", "AfterResponseHookHandler"),
    ("py:class", "BeforeRequestHookHandler"),
    ("py:class", "ExceptionHandlersMap"),
    ("py:class", "Guard"),
    ("py:class", "Middleware"),
    ("py:class", "ParametersMap"),
    ("py:class", "ResponseCookies"),
    ("py:class", "ResponseType"),
    ("py:class", "TypeEncodersMap"),
]
nitpick_ignore_regex = [
    (r"py:.*", r"starlite\.types.*"),
    (r"py:.*", r"starlite.*\.T"),
    (r"py:.*", r".*R_co"),
    (r"py:.*", r"starlite\.security\.base\.UserType"),
    (r"py:.*", r"starlite\.middleware\.session\.base\.BaseSessionBackendT"),
    (r"py:obj", r"typing\..*"),
]

# Warnings about missing references to those targets in the specified location will be ignored.
# The source of the references is taken 1:1 from the warnings as reported by Sphinx, e.g
# **/starlite/testing/client/async_client.py:docstring of starlite.testing.AsyncTestClient.exit_stack:1: WARNING: py:class reference target not found: AsyncExitStack
# would be added as: "starlite.testing.AsyncTestClient.exit_stack": {"AsyncExitStack"},
ignore_missing_refs = {
    # autodoc thinks it's a py:class: but it's a py:data. TODO: Fix this. Should be possible I think
    # "starlite.router.Router.__init__": {"TypeEncodersMap"},
    # No idea what autodoc is doing here. Possibly unfixable on our end
    "starlite.testing.BaseTestClient.blocking_portal": {"BlockingPortal"},
    "starlite.template.base.TemplateEngineProtocol.get_template": {"starlite.template.base.T_co"},
    "starlite.template": {"starlite.template.base.T_co"},
    "starlite.testing.WebSocketTestSession.exit_stack": {"ExitStack"},
    "starlite.testing.TestClient.exit_stack": {"ExitStack"},
    "starlite.testing.AsyncTestClient.exit_stack": {"AsyncExitStack"},
    "starlite.security.session_auth.middleware.SessionAuthMiddleware.__init__": {"Scopes"},
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
