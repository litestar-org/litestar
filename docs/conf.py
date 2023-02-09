import importlib.metadata

project = "Starlite"
copyright = "2023, Starlite-API"
author = "Starlite-API"
release = importlib.metadata.version("starlite").rsplit(".")[0]

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

html_theme = "pydata_sphinx_theme"
html_static_path = ["_static"]
html_css_files = ["style.css"]
html_js_files = ["versioning.js"]
html_favicon = "images/favicon.ico"
html_logo = "images/logo.svg"
html_show_sourcelink = False
html_sidebars = {"about/*": []}

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
}


html_context = {
    "navbar_items": {
        "Documentation": "/lib",
        "Community": {
            "Contribution guide": "/community/contribution-guide.html",
            "Code of Conduct": "https://github.com/starlite-api/starlite/blob/main/CODE_OF_CONDUCT.md",
        },
        "About": {
            "Organization": "/about/organization.html",
            "Releases": "/about/starlite-releases.html",
        },
        "Release notes": "/release-notes",
    }
}
