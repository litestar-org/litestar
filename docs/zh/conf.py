from __future__ import annotations

import importlib.metadata
import json
import os
import sys
import warnings
from datetime import datetime
from pathlib import Path

from sphinx.application import Sphinx
from sqlalchemy.exc import SAWarning

warnings.filterwarnings("ignore", category=SAWarning)

__all__ = ["setup"]

sys.path.insert(0, str(Path(__file__).parent.parent))

PY_CLASS = "py:class"
PY_RE = r"py:.*"
PY_METH = "py:meth"
PY_ATTR = "py:attr"
PY_OBJ = "py:obj"
PY_FUNC = "py:func"

current_year = datetime.now().year
project = "Litestar 中文文档"
copyright = f"{current_year}, Litestar 贡献者"
author = "Litestar 组织"
language = "zh_CN"
release = os.getenv("_LITESTAR_DOCS_BUILD_VERSION", importlib.metadata.version("litestar").rsplit(".")[0])
environment = os.getenv("_LITESTAR_DOCS_BUILD_ENVIRONMENT", "local")

rst_epilog = f"""
.. |version| replace:: {release}
"""

extensions = [
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosectionlabel",
    "sphinx_design",
    "auto_pytabs.sphinx_ext",
    "sphinx_copybutton",
    "sphinxcontrib.mermaid",
    "sphinx_click",
    "sphinx_paramlinks",
    "sphinx_togglebutton",
]

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "msgspec": ("https://jcristharif.com/msgspec/", None),
    "anyio": ("https://anyio.readthedocs.io/en/stable/", None),
    "multidict": ("https://multidict.aio-libs.org/en/stable/", None),
    "cryptography": ("https://cryptography.io/en/latest/", None),
    "sqlalchemy": ("https://docs.sqlalchemy.org/en/20/", None),
    "alembic": ("https://alembic.sqlalchemy.org/en/latest/", None),
    "click": ("https://click.palletsprojects.com/en/latest/", None),
    "redis": ("https://redis.readthedocs.io/en/stable/", None),
    "structlog": ("https://www.structlog.org/en/stable/", None),
    "tortoise": ("https://tortoise.github.io/", None),
    "opentelemetry": ("https://opentelemetry-python.readthedocs.io/en/latest/", None),
    "advanced-alchemy": ("https://docs.advanced-alchemy.litestar.dev/latest/", None),
    "jinja2": ("https://jinja.palletsprojects.com/en/latest/", None),
    "trio": ("https://trio.readthedocs.io/en/stable/", None),
    "pydantic": ("https://docs.pydantic.dev/latest/", None),
    "typing_extensions": ("https://typing-extensions.readthedocs.io/en/stable/", None),
    "valkey": ("https://valkey-py.readthedocs.io/en/latest/", None),
    "fsspec": ("https://filesystem-spec.readthedocs.io/en/latest/", None),
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
autodoc_mock_imports = []

nitpicky = True
nitpick_ignore = [
    (PY_CLASS, "BaseModel"),
    (PY_CLASS, "ExternalType"),
    (PY_CLASS, "TypeEngine"),
    (PY_CLASS, "UserDefinedType"),
    (PY_CLASS, "_RegistryType"),
    (PY_CLASS, "_orm.Mapper"),
    (PY_CLASS, "_orm.registry"),
    (PY_CLASS, "_schema.MetaData"),
    (PY_CLASS, "_schema.Table"),
    (PY_CLASS, "_types.TypeDecorator"),
    (PY_CLASS, "abc.Collection"),
    (PY_CLASS, "advanced_alchemy.utils.dataclass.Empty"),
    (PY_CLASS, "jinja2.environment.Environment"),
    (PY_CLASS, "mako.lookup.TemplateLookup"),
    (PY_CLASS, "mako.template.Template"),
    (PY_CLASS, "minijinja.Environment"),
    (PY_CLASS, "pydantic.BaseModel"),
    (PY_CLASS, "pydantic.generics.GenericModel"),
    (PY_CLASS, "pydantic.main.BaseModel"),
    (PY_CLASS, "redis.asyncio.Redis"),
    (PY_CLASS, "sqlalchemy.dialects.postgresql.named_types.ENUM"),
    (PY_CLASS, "sqlalchemy.orm.decl_api.DeclarativeMeta"),
    (PY_CLASS, "sqlalchemy.sql.sqltypes.TupleType"),
    (PY_CLASS, "valkey.asyncio.Valkey"),
    (PY_METH, "_types.TypeDecorator.process_bind_param"),
    (PY_METH, "_types.TypeDecorator.process_result_value"),
    (PY_METH, "litestar.typing.ParsedType.is_subclass_of"),
    (PY_METH, "type_engine"),
    (PY_CLASS, "OperationIDCreator"),
    (PY_CLASS, "ProblemDetailsExceptionHandlerType"),
    (PY_CLASS, "ClientRequestHookHandler"),
    (PY_CLASS, "ClientResponseHookHandler"),
    (PY_CLASS, "ServerRequestHookHandler"),
    (PY_CLASS, "AnyIOBackend"),
    (PY_CLASS, "BaseSessionBackendT"),
    (PY_CLASS, "C"),
    (PY_CLASS, "CollectionT"),
    (PY_CLASS, "ControllerRouterHandler"),
    (PY_CLASS, "EmptyType"),
    (PY_CLASS, "ModelT"),
    (PY_CLASS, "PathParameterDefinition"),
    (PY_CLASS, "RouteHandlerType"),
    (PY_CLASS, "SelectT"),
    (PY_CLASS, "T"),
    (PY_OBJ, "litestar.security.base.AuthType"),
    (PY_CLASS, "Environment"),
    (PY_CLASS, "P"),
    (PY_CLASS, "pydantic_v2.BaseModel"),
    (PY_CLASS, "pydantic.BaseModel"),
    (PY_CLASS, "advanced_alchemy.config.types.Empty"),
    (PY_OBJ, "litestar.template.base.TemplateType_co"),
    (PY_OBJ, "litestar.template.base.ContextType_co"),
    (PY_CLASS, "litestar.template.base.TemplateType_co"),
    (PY_CLASS, "litestar.template.base.ContextType_co"),
    (PY_CLASS, "litestar.template.base.ContextType"),
    (PY_CLASS, "litestar.template.base.R"),
    (PY_CLASS, "BacklogStrategy"),
    (PY_CLASS, "ExceptionT"),
    (PY_CLASS, "NoneType"),
    (PY_CLASS, "litestar._openapi.schema_generation.schema.SchemaCreator"),
    (PY_CLASS, "litestar._signature.model.SignatureModel"),
    (PY_CLASS, "litestar.utils.signature.ParsedSignature"),
    (PY_CLASS, "litestar.utils.sync.AsyncCallable"),
    (PY_ATTR, "litestar.dto.factory.DTOConfig.underscore_fields_private"),
    (PY_CLASS, "anyio.abc.BlockingPortal"),
    (PY_CLASS, "litestar.contrib.sqlalchemy.types.JsonB"),
    (PY_CLASS, "litestar.contrib.sqlalchemy.plugins.SQLAlchemyInitPlugin"),
    (PY_CLASS, "litestar.contrib.msgspec.MsgspecDTO"),
    (PY_CLASS, "litestar.contrib.repository.filters.NotInCollectionFilter"),
    (PY_CLASS, "litestar.contrib.repository.filters.NotInSearchFilter"),
    (PY_CLASS, "litestar.contrib.repository.filters.OnBeforeAfter"),
    (PY_CLASS, "litestar.contrib.repository.filters.OrderBy"),
    (PY_CLASS, "litestar.contrib.repository.filters.SearchFilter"),
    (PY_CLASS, "litestar.dto.base_factory.AbstractDTOFactory"),
    (PY_CLASS, "litestar.dto.factory.DTOConfig"),
    (PY_CLASS, "litestar.dto.factory.DTOData"),
    (PY_CLASS, "litestar.dto.interface.DTOInterface"),
    (PY_CLASS, "litestar.partial.Partial"),
    (PY_CLASS, "litestar.response.RedirectResponse"),
    (PY_CLASS, "litestar.response_containers.Redirect"),
    (PY_CLASS, "litestar.response_containers.Template"),
    (PY_CLASS, "litestar.contrib.htmx.request.HTMXRequest"),
    (PY_CLASS, "litestar.typing.ParsedType"),
    (PY_METH, "litestar.dto.factory.DTOData.create_instance"),
    (PY_METH, "litestar.dto.interface.DTOInterface.data_to_encodable_type"),
    (PY_CLASS, "MetaData"),
    (PY_FUNC, "sqlalchemy.get_engine"),
    (PY_OBJ, "litestar.template.base.T_co"),
    ("py:exc", "RepositoryError"),
    ("py:exc", "InternalServerError"),
    ("py:exc", "HTTPExceptions"),
    (PY_CLASS, "litestar.template.Template"),
    (PY_CLASS, "litestar.middleware.compression.gzip_facade.GzipCompression"),
    (PY_CLASS, "litestar.openapi.OpenAPIController"),
    (PY_CLASS, "openapi.controller.OpenAPIController"),
    (PY_CLASS, "litestar.handlers.http_handlers.decorators._subclass_warning"),
    (PY_CLASS, "litestar.background_tasks.P"),
    (PY_CLASS, "P.args"),
    (PY_CLASS, "P.kwargs"),
    (PY_CLASS, "litestar.contrib.jinja.P"),
    (PY_CLASS, "litestar.contrib.mako.P"),
    (PY_CLASS, "JWTDecodeOptions"),
    (PY_CLASS, "litestar.template.base.P"),
    (PY_CLASS, "litestar.contrib.pydantic.PydanticDTO"),
    (PY_CLASS, "litestar.contrib.pydantic.PydanticPlugin"),
    (PY_CLASS, "typing.Self"),
    (PY_CLASS, "attr.AttrsInstance"),
    (PY_CLASS, "typing_extensions.TypeGuard"),
    (PY_CLASS, "advanced_alchemy.types.BigIntIdentity"),
]

nitpick_ignore_regex = [
    (PY_ATTR, "litestar.repository.testing.AsyncGenericMockRepository.id_attribute"),
    (PY_ATTR, "litestar.repository.AbstractAsyncRepository.id_attribute"),
    (PY_ATTR, "litestar.repository.AbstractSyncRepository.id_attribute"),
    (PY_OBJ, r"typing\..*"),
    (PY_RE, r".*R_co"),
    (PY_RE, r".*UserType"),
    (PY_RE, r"ModelT"),
    (PY_RE, r"litestar.*\.T"),
    (PY_RE, r"litestar\.middleware\.session\.base\.BaseSessionBackendT"),
    (PY_RE, r"litestar\.types.*"),
    (PY_RE, r"httpx.*"),
    (PY_RE, r"litestar.middleware.session.base.ConfigT"),
    (PY_RE, r"litestar\.connection\.base\.AuthT"),
    (PY_RE, r"litestar\.connection\.base\.HandlerT"),
    (PY_RE, r"litestar\.connection\.base\.StateT"),
    (PY_RE, r"litestar\.connection\.base\.UserT"),
    (PY_RE, r"litestar\.pagination\.C"),
    (PY_RE, r"multidict\..*"),
    (PY_RE, r"advanced_alchemy.*\.T"),
    (PY_RE, r"advanced_alchemy\.config\.common\.EngineT"),
    (PY_RE, r"advanced_alchemy\.config\.common\.SessionT"),
    (PY_RE, r".*R"),
    (PY_RE, r".*ScopeT"),
    (PY_OBJ, r"litestar.security.jwt.auth.TokenT"),
    (PY_CLASS, "ExceptionToProblemDetailMapType"),
    (PY_CLASS, "litestar.security.jwt.token.JWTDecodeOptions"),
    (PY_RE, r"^Mapping\[(str|int)$"),
    (PY_RE, r"^dict\[str$"),
    (PY_RE, r"^Literal\[.*$"),
    (PY_RE, r"^set\[~?typing\.Literal\[.*$"),
]

ignore_missing_refs = {
    "litestar.template.base.TemplateEngineProtocol.get_template": {"litestar.template.base.T_co"},
    "litestar.template": {"litestar.template.base.T_co"},
    "litestar.response.file.async_file_iterator": {"FileSystemAdapter"},
    re.compile("litestar.response.redirect.*"): {"RedirectStatusType"},
    re.compile(r"litestar\.plugins.*"): re.compile(".*ModelT"),
    re.compile(r"litestar\.(contrib|repository)\.*"): re.compile(".*T"),
    re.compile(r"litestar\.contrib\.sqlalchemy\.*"): re.compile(
        ".*(ConnectionT|EngineT|SessionT|SessionMakerT|SlotsBase)"
    ),
    re.compile(r"litestar\.dto.*"): re.compile(".*T|.*FieldDefinition|Empty"),
    re.compile(r"litestar\.template\.(config|TemplateConfig).*"): re.compile(".*EngineType"),
    "litestar.concurrency.set_asyncio_executor": {"ThreadPoolExecutor"},
    "litestar.concurrency.get_asyncio_executor": {"ThreadPoolExecutor"},
    re.compile(r"litestar\.channels\.backends\.asyncpg.*"): {"asyncpg.connection.Connection", "asyncpg.Connection"},
    re.compile(r"litestar\.handlers\.websocket_handlers\.stream.*"): {"WebSocketMode"},
    re.compile(r"litestar\.file_system.*"): {"AnyFileSystem", "SymlinkResolver"},
    re.compile(r"litestar\.logging\.structlog\.StructLoggingConfig"): {
        "structlog.typing.Processor",
        "structlog.typing.Context",
        "structlog.typing.WrappedLogger",
    },
}

linkcheck_ignore = [
    r"http://localhost(:\d+)?",
    r"http://127.0.0.1(:\d+)?",
    "http://testserver",
]

auto_pytabs_min_version = (3, 11)
auto_pytabs_max_version = (3, 14)
auto_pytabs_compat_mode = True

autosectionlabel_prefix_document = True

suppress_warnings = [
    "autosectionlabel.*",
    "ref.python",
]

html_theme = "litestar_sphinx_theme"
html_title = "Litestar 中文文档"
html_short_title = "Litestar"

pygments_style = "one-light"

html_static_path = ["../_static"]
templates_path = ["../_templates"]
html_css_files = ["style.css"]

html_favicon = "../_static/favicon.svg"

html_show_sourcelink = True
html_copy_source = True
html_sourcelink_suffix = ""

html_context = {
    "source_type": "github",
    "source_user": "litestar-org",
    "source_repo": "litestar",
    "source_version": os.getenv("LITESTAR_DOCS_SOURCE_REF", "main"),
    "current_version": release,
    "current_language": "zh",
    "language": "zh_CN",
    "doc_lang": "zh",
    "languages": [
        ("en", "English"),
        ("zh", "中文"),
    ],
}

html_theme_options = {
    "logo_target": "/zh/",
    "github_repo_name": "litestar",
    "navigation_with_keys": True,
    "nav_links": [
        {"title": "首页", "url": "index"},
        {
            "title": "社区",
            "children": [
                {
                    "title": "贡献指南",
                    "summary": "了解如何为 Litestar 项目做出贡献",
                    "url": "contribution-guide",
                    "icon": "contributing",
                },
                {
                    "title": "行为准则",
                    "summary": "回顾与 Litestar 社区互动的礼仪",
                    "url": "https://github.com/litestar-org/.github?tab=coc-ov-file",
                    "icon": "coc",
                },
                {
                    "title": "安全",
                    "summary": "Litestar 安全协议概述",
                    "url": "https://github.com/litestar-org/.github?tab=coc-ov-file#security-ov-file",
                    "icon": "coc",
                },
            ],
        },
        {
            "title": "关于",
            "children": [
                {
                    "title": "Litestar 组织",
                    "summary": "关于 Litestar 组织的详细信息",
                    "url": "https://litestar.dev/about/organization",
                    "icon": "org",
                },
                {
                    "title": "发布说明",
                    "summary": "探索 Litestar 的发布过程、版本控制和弃用策略",
                    "url": "https://litestar.dev/about/litestar-releases",
                    "icon": "releases",
                },
            ],
        },
        {
            "title": "发布说明",
            "children": [
                {
                    "title": "3.0 新功能",
                    "url": "release-notes/whats-new-3",
                    "summary": "探索 Litestar 3.0 的新功能",
                },
                {
                    "title": "3.x 更新日志",
                    "url": "release-notes/changelog",
                    "summary": "3.x 系列的所有变更",
                },
                {
                    "title": "2.x 更新日志",
                    "url": "https://docs.litestar.dev/2/release-notes/changelog.html",
                    "summary": "2.x 系列的所有变更",
                },
            ],
        },
        {
            "title": "帮助",
            "children": [
                {
                    "title": "Discord 帮助论坛",
                    "summary": "专门的 Discord 帮助论坛",
                    "url": "https://discord.gg/litestar",
                    "icon": "coc",
                },
                {
                    "title": "GitHub 讨论",
                    "summary": "GitHub 讨论",
                    "url": "https://github.com/orgs/litestar-org/discussions",
                    "icon": "coc",
                },
                {
                    "title": "Stack Overflow",
                    "summary": "我们在 Stack Overflow 上监控 <code><b>litestar</b></code> 标签",
                    "url": "https://stackoverflow.com/questions/tagged/litestar",
                    "icon": "coc",
                },
            ],
        },
        {"title": "赞助", "url": "https://github.com/sponsors/Litestar-Org", "icon": "heart"},
    ],
}

if environment != "latest":
    html_theme_options["announcement"] = (
        f"您正在查看文档的 <strong>{environment}</strong> 版本。"
        f'<a href="/latest/">点击此处查看最新版本。</a>'
    )


def delayed_setup(app: Sphinx) -> None:
    if app.builder.name == "linkcheck":
        return
    app.setup_extension("shibuya")


def setup(app: Sphinx) -> dict[str, bool]:
    app.connect("builder-inited", delayed_setup, priority=0)
    app.setup_extension("litestar_sphinx_theme")
    return {"parallel_read_safe": True, "parallel_write_safe": True}
