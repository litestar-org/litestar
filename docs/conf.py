import importlib.metadata

project = "Starlite"
copyright = "2023, Starlite-API"
author = "Starlite-API"
# release = "1.48.1"
release = importlib.metadata.version("starlite")

extensions = [
    "sphinx.ext.intersphinx",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_design",
    "myst_parser",
    "tools.sphinx_ext",
    "auto_pytabs.sphinx_ext",
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
autodoc_default_options = {"special-members": "__init__", "show-inheritance": True}
autodoc_member_order = "bysource"
autodoc_typehints_format = "short"

auto_pytabs_no_cache = True
auto_pytabs_min_version = (3, 8)
auto_pytabs_max_version = (3, 11)

autosectionlabel_prefix_document = True


html_theme = "furo"
html_static_path = ["_static"]
html_favicon = "images/starlite-favicon.ico"

html_theme_options = {
    "footer_icons": [
        {
            "name": "GitHub",
            "url": "https://github.com/starlite-api/starlite",
            "html": """
                <svg stroke="currentColor" fill="currentColor" stroke-width="0" viewBox="0 0 16 16">
                    <path fill-rule="evenodd" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z"></path>
                </svg>
            """,
            "class": "",
        },
    ],
    "light_logo": "images/starlite-logo-light.svg",
    "dark_logo": "images/starlite-logo-transparent.svg",
    "source_repository": "https://github.com/starlite-api/starlite",
    "source_branch": "main",
    "source_directory": "docs/",
    "sidebar_hide_name": True,
    "dark_css_variables": {
        "color-sidebar-background": "#1d2433",
        "color-background-primary": "#0c101a",
        "color-brand-content": "#ffae57",
        "color-brand-primary": "#ffae57",
    },
    "light_css_variables": {
        "color-brand-content": "#f2830d",
        "color-brand-primary": "#f2830d",
    },
}
