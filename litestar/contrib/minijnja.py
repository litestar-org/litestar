from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from litestar.exceptions import ImproperlyConfiguredException, MissingDependencyException, TemplateNotFoundException
from litestar.template.base import (
    TemplateEngineProtocol,
    TemplateProtocol,
    csrf_token,
    url_for,
    url_for_static_asset,
)

__all__ = ("MiniJinjaTemplateEngine",)


try:
    import minijinja as m  # noqa: F401
except ImportError as e:
    raise MissingDependencyException("minijinja") from e

from minijinja import Environment, pass_state
from minijinja import TemplateError as MiniJinjaTemplateNotFound

if TYPE_CHECKING:
    from pydantic import DirectoryPath


class MiniJinjaTemplate(TemplateProtocol):
    """Initialize a template.

    Args:
        template: Base ``MiniJinjaTemplate`` used by the underlying minijinja engine
    """

    def __init__(self, engine: Environment, template_name: str) -> None:
        super().__init__()
        self.engine = engine
        self.template_name = template_name

    def render(self, *args: Any, **kwargs: Any) -> str:
        """Render a template.

        Args:
            args: Positional arguments passed to the engines ``render`` function
            kwargs: Keyword arguments passed to the engines ``render`` function

        Returns:
            Rendered template as a string
        """
        return str(self.engine.render_template(self.template_name, *args, **kwargs))


class MiniJinjaTemplateEngine(TemplateEngineProtocol["MiniJinjaTemplate"]):
    """The engine instance."""

    def __init__(
        self, directory: DirectoryPath | list[DirectoryPath] | None = None, engine_instance: Environment | None = None
    ) -> None:
        """Minijinja based TemplateEngine.

        Args:
            directory: Direct path or list of directory paths from which to serve templates.
            engine_instance: A Minijinja Environment instance.
        """
        super().__init__(directory, engine_instance)
        if directory and engine_instance:
            raise ImproperlyConfiguredException(
                "You must provide either a directory or a minijinja Environment instance."
            )
        if directory:

            def _loader(name: str) -> str:
                """Load a template from a directory.

                Args:
                    name: The name of the template

                Returns:
                    The template as a string

                Raises:
                    TemplateNotFoundException: if no template is found.
                """
                directories = [directory] if not isinstance(directory, list) else directory

                for d in directories:
                    template_path = Path(d) / name  # pyright: ignore[reportGeneralTypeIssues]
                    if template_path.exists():
                        return template_path.read_text()
                raise TemplateNotFoundException(template_name=name)

            self.engine = Environment(loader=_loader)
        elif engine_instance:
            self.engine = engine_instance
        self.register_template_callable(key="url_for_static_asset", template_callable=url_for_static_asset)  # type: ignore
        self.register_template_callable(key="csrf_token", template_callable=csrf_token)  # type: ignore
        self.register_template_callable(key="url_for", template_callable=url_for)  # type: ignore

    def get_template(self, template_name: str) -> MiniJinjaTemplate:
        """Retrieve a template by matching its name (dotted path) with files in the directory or directories provided.

        Args:
            template_name: A dotted path

        Returns:
            MiniJinjaTemplate instance

        Raises:
            TemplateNotFoundException: if no template is found.
        """
        try:
            return MiniJinjaTemplate(self.engine, template_name)
        except MiniJinjaTemplateNotFound as exc:
            raise TemplateNotFoundException(template_name=template_name) from exc

    def register_template_callable(self, key: str, template_callable: Callable[[dict[str, Any]], Any]) -> None:
        """Register a callable on the template engine.

        Args:
            key: The callable key, i.e. the value to use inside the template to call the callable.
            template_callable: A callable to register.

        Returns:
            None
        """
        self.engine.add_global(key, pass_state(template_callable))

    @classmethod
    def from_environment(cls, minijinja_environment: Environment) -> MiniJinjaTemplateEngine:
        """Create a MiniJinjaTemplateEngine from an existing minijinja Environment instance.

        Args:
            minijinja_environment (Environment): A minijinja Environment instance.

        Returns:
            MiniJinjaTemplateEngine instance
        """
        return cls(directory=None, engine_instance=minijinja_environment)
