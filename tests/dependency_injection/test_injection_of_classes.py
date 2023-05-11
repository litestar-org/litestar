from litestar import Controller, get
from litestar.di import Provide
from litestar.testing import create_test_client


def test_injection_of_classes() -> None:
    query_param_value = 5
    path_param_value = 10

    class TopLevelDependency:
        def __init__(self, path_param: int) -> None:
            self.path_param = path_param

    class HandlerDependency:
        def __init__(self, query_param: int, path_param_dependency: TopLevelDependency):
            self.query_param = query_param
            self.path_param_dependency = path_param_dependency

    class MyController(Controller):
        path = "/test"
        dependencies = {"path_param_dependency": Provide(TopLevelDependency, sync_to_thread=False)}

        @get(
            path="/{path_param:int}",
            dependencies={
                "container": Provide(HandlerDependency, sync_to_thread=False),
            },
        )
        def test_function(self, container: HandlerDependency) -> str:
            assert container
            assert isinstance(container, HandlerDependency)
            assert container.query_param == query_param_value
            assert isinstance(container.path_param_dependency, TopLevelDependency)
            assert container.path_param_dependency.path_param == path_param_value
            return str(container.query_param + container.path_param_dependency.path_param)

    with create_test_client(MyController) as client:
        response = client.get(f"/test/{path_param_value}?query_param={query_param_value}")
        assert response.text == "15"
