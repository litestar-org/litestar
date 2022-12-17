from typing import TYPE_CHECKING, Any, Callable, Dict, List, Union

from starlite.exceptions import MissingDependencyException, TemplateNotFoundException
from starlite.template.base import (
    TemplateEngineProtocol,
    csrf_token,
    url_for,
    url_for_static_asset,
)

try:
    from jinja2 import Environment, FileSystemLoader
    from jinja2 import TemplateNotFound as JinjaTemplateNotFound
    from jinja2 import pass_context
except ImportError as e:
    raise MissingDependencyException("jinja2 is not installed") from e

if TYPE_CHECKING:
    from jinja2 import Template as JinjaTemplate
    from pydantic import DirectoryPath


class JinjaTemplateEngine(TemplateEngineProtocol["JinjaTemplate"]):
    """The engine instance."""

    def __init__(self, directory: Union["DirectoryPath", List["DirectoryPath"]]) -> None:
        """Jinja2 based TemplateEngine.

        Args:
            directory: Direct path or list of directory paths from which to serve templates.
        """
        super().__init__(directory=directory)
        loader = FileSystemLoader(searchpath=directory)
        self.engine = Environment(loader=loader, autoescape=True)
        self.register_template_callable(key="url_for_static_asset", template_callable=url_for_static_asset)  # type: ignore
        self.register_template_callable(key="csrf_token", template_callable=csrf_token)  # type: ignore
        self.register_template_callable(key="url_for", template_callable=url_for)  # type: ignore

    def get_template(self, template_name: str) -> "JinjaTemplate":
        """Retrieve a template by matching its name (dotted path) with files in the directory or directories provided.
        Args:
            template_name: A dotted path

        Returns:
            JinjaTemplate instance

        Raises:
            [TemplateNotFoundException][starlite.exceptions.TemplateNotFoundException]: if no template is found.
        """
        try:
            return self.engine.get_template(name=template_name)
        except JinjaTemplateNotFound as exc:
            raise TemplateNotFoundException(template_name=template_name) from exc

    def register_template_callable(self, key: str, template_callable: Callable[[Dict[str, Any]], Any]) -> None:
        """Register a callable on the template engine.

        Args:
            key: The callable key, i.e. the value to use inside the template to call the callable.
            template_callable: A callable to register.

        Returns:
            None
        """
        self.engine.globals[key] = pass_context(template_callable)
