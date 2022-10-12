from pathlib import Path

from starlite import Template, TemplateConfig, get
from starlite.template.jinja import JinjaTemplateEngine
from starlite.template.mako import MakoTemplateEngine
from starlite.testing import create_test_client


def test_jinja_url_for(template_dir: Path) -> None:
    template_config = TemplateConfig(engine=JinjaTemplateEngine, directory=template_dir)

    @get(path="/")
    def tpl_renderer() -> Template:
        return Template(name="tpl.html")

    @get(path="/simple", name="simple")
    def simple_handler() -> None:
        pass

    @get(path="/complex/{int_param:int}/{time_param:time}", name="complex")
    def complex_handler() -> None:
        pass

    with create_test_client(
        route_handlers=[simple_handler, complex_handler, tpl_renderer], template_config=template_config
    ) as client:
        Path(template_dir / "tpl.html").write_text("{{ url_for('simple') }}")

        response = client.get("/")
        assert response.status_code == 200
        assert response.text == "/simple"

    with create_test_client(
        route_handlers=[simple_handler, complex_handler, tpl_renderer], template_config=template_config
    ) as client:
        Path(template_dir / "tpl.html").write_text("{{ url_for('complex', int_param=100, time_param='18:00') }}")

        response = client.get("/")
        assert response.status_code == 200
        assert response.text == "/complex/100/18:00"

    with create_test_client(
        route_handlers=[simple_handler, complex_handler, tpl_renderer], template_config=template_config
    ) as client:
        # missing route params should cause 500 err
        Path(template_dir / "tpl.html").write_text("{{ url_for('complex') }}")
        response = client.get("/")
        assert response.status_code == 500

    with create_test_client(
        route_handlers=[simple_handler, complex_handler, tpl_renderer], template_config=template_config
    ) as client:
        # wrong param type should also cause 500 error
        Path(template_dir / "tpl.html").write_text("{{ url_for('complex', int_param='100', time_param='18:00') }}")

        response = client.get("/")
        assert response.status_code == 500

    with create_test_client(
        route_handlers=[simple_handler, complex_handler, tpl_renderer], template_config=template_config
    ) as client:
        Path(template_dir / "tpl.html").write_text("{{ url_for('non-existent-route') }}")

        response = client.get("/")
        assert response.status_code == 500


def test_mako_url_for(template_dir: Path) -> None:
    template_config = TemplateConfig(engine=MakoTemplateEngine, directory=template_dir)

    @get(path="/")
    def tpl_renderer() -> Template:
        return Template(name="tpl.html")

    @get(path="/simple", name="simple")
    def simple_handler() -> None:
        pass

    @get(path="/complex/{int_param:int}/{time_param:time}", name="complex")
    def complex_handler() -> None:
        pass

    with create_test_client(
        route_handlers=[simple_handler, complex_handler, tpl_renderer], template_config=template_config
    ) as client:
        Path(template_dir / "tpl.html").write_text("${url_for('simple')}")

        response = client.get("/")
        assert response.status_code == 200
        assert response.text == "/simple"

    with create_test_client(
        route_handlers=[simple_handler, complex_handler, tpl_renderer], template_config=template_config
    ) as client:
        Path(template_dir / "tpl.html").write_text("${url_for('complex', int_param=100, time_param='18:00')}")

        response = client.get("/")
        assert response.status_code == 200
        assert response.text == "/complex/100/18:00"

    with create_test_client(
        route_handlers=[simple_handler, complex_handler, tpl_renderer], template_config=template_config
    ) as client:
        # missing route params should cause 500 err
        Path(template_dir / "tpl.html").write_text("${url_for('complex')}")
        response = client.get("/")
        assert response.status_code == 500

    with create_test_client(
        route_handlers=[simple_handler, complex_handler, tpl_renderer], template_config=template_config
    ) as client:
        # wrong param type should also cause 500 error
        Path(template_dir / "tpl.html").write_text("${url_for('complex', int_param='100', time_param='18:00')}")

        response = client.get("/")
        assert response.status_code == 500

    with create_test_client(
        route_handlers=[simple_handler, complex_handler, tpl_renderer], template_config=template_config
    ) as client:
        Path(template_dir / "tpl.html").write_text("${url_for('non-existent-route')}")

        response = client.get("/")
        assert response.status_code == 500
