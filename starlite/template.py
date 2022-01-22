from typing import Any, Dict, List, Union

from typing_extensions import Protocol, runtime_checkable

from starlite.exceptions import MissingDependencyException


@runtime_checkable
class Template(Protocol):
    def render(self, context: Dict[str, Any]) -> str:
        ...


@runtime_checkable
class TemplateEngineProtocol(Protocol):
    directory: str

    def get_template(self, name: str) -> Template:
        ...


class JinjaTemplateEngine:
    __slots__ = ("_engine", "directory")

    def __init__(self, directory: Union[str, List[str]]) -> None:
        try:
            import jinja2  # pylint: disable=C0415
        except ImportError as e:
            raise MissingDependencyException("jinja2 is not installed") from e

        self.directory = directory
        loader = jinja2.FileSystemLoader(searchpath=directory)
        self._engine = jinja2.Environment(loader=loader, autoescape=True)

    def get_template(self, name: str) -> Template:
        return self._engine.get_template(name=name)


class MakoTemplateEngine:
    __slots__ = ("_engine", "directory")

    def __init__(self, directory: Union[str, List[str]]) -> None:
        try:
            from mako.lookup import TemplateLookup  # pylint: disable=C0415
        except ImportError as e:
            raise MissingDependencyException("mako is not installed") from e

        self.directory = directory
        self._engine = TemplateLookup([directory])

    def get_template(self, name: str) -> Template:
        return self._engine.get_template(name)
