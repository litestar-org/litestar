from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from litestar.exceptions import ImproperlyConfiguredException, MissingDependencyException, TemplateNotFoundException
from litestar.template.base import (
    TemplateEngineProtocol,
    csrf_token,
    url_for,
    url_for_static_asset,
)

__all__ = ("JinjaTemplateEngine",)


try:
    import jinja2  # noqa: F401
except ImportError as e:
    raise MissingDependencyException("jinja2") from e

from jinja2 import Environment, FileSystemLoader, pass_context
from jinja2 import TemplateNotFound as JinjaTemplateNotFound

if TYPE_CHECKING:
    from jinja2 import Template as JinjaTemplate
    from pydantic import DirectoryPath


class JinjaTemplateEngine(TemplateEngineProtocol["JinjaTemplate"]):
    """The engine instance."""

    def __init__(
        self,
        directory: DirectoryPath | list[DirectoryPath] | None = None,
        engine_instance: Environment | None = None,
    ) -> None:
        """Jinja based TemplateEngine.

        Args:
            directory: Direct path or list of directory paths from which to serve templates.
            engine_instance: A jinja Environment instance.
        """

        super().__init__(directory, engine_instance)
        if directory and engine_instance:
            raise ImproperlyConfiguredException("You must provide either a directory or a jinja2 Environment instance.")
        if directory:
            loader = FileSystemLoader(searchpath=directory)
            self.engine = Environment(loader=loader, autoescape=True)
        elif engine_instance:
            self.engine = engine_instance
        self.register_template_callable(key="url_for_static_asset", template_callable=url_for_static_asset)  # type: ignore
        self.register_template_callable(key="csrf_token", template_callable=csrf_token)  # type: ignore
        self.register_template_callable(key="url_for", template_callable=url_for)  # type: ignore

    def get_template(self, template_name: str) -> JinjaTemplate:
        """Retrieve a template by matching its name (dotted path) with files in the directory or directories provided.

        Args:
            template_name: A dotted path

        Returns:
            JinjaTemplate instance

        Raises:
            TemplateNotFoundException: if no template is found.
        """
        try:
            return self.engine.get_template(name=template_name)
        except JinjaTemplateNotFound as exc:
            raise TemplateNotFoundException(template_name=template_name) from exc

    def register_template_callable(self, key: str, template_callable: Callable[[dict[str, Any]], Any]) -> None:
        """Register a callable on the template engine.

        Args:
            key: The callable key, i.e. the value to use inside the template to call the callable.
            template_callable: A callable to register.

        Returns:
            None
        """
        self.engine.globals[key] = pass_context(template_callable)

    @classmethod
    def from_environment(cls, jinja_environment: Environment) -> JinjaTemplateEngine:
        """Create a JinjaTemplateEngine from an existing jinja Environment instance.

        Args:
            jinja_environment (jinja2.environment.Environment): A jinja Environment instance.

        Returns:
            JinjaTemplateEngine instance
        """
        return cls(directory=None, engine_instance=jinja_environment)
