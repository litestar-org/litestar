from __future__ import annotations

from litestar import get, post
from litestar.app import AppConfig, Litestar
from litestar.config.response_cache import ResponseCacheConfig
from litestar.openapi.config import OpenAPIConfig
from litestar.testing import TestClient


class TestAppConfigIntegration:
    def test_basic_app_functionality(self):
        @get("/")
        async def handler() -> dict[str, str]:
            return {"message": "Hello World"}

        config = AppConfig(route_handlers=[handler])
        app1 = Litestar.from_config(config)

        app2 = Litestar(route_handlers=[handler])

        with TestClient(app1) as client1, TestClient(app2) as client2:
            response1 = client1.get("/")
            response2 = client2.get("/")

            assert response1.status_code == response2.status_code == 200
            assert response1.json() == response2.json() == {"message": "Hello World"}

    def test_logging_functionality(self):
        @get("/test")
        async def handler() -> dict[str, str]:
            return {"test": "logging"}

        config = AppConfig(route_handlers=[handler])
        app1 = Litestar.from_config(config)

        app2 = Litestar(route_handlers=[handler])

        logger1 = app1.get_logger("test")
        logger2 = app2.get_logger("test")

        assert logger1 is not None
        assert logger2 is not None
        assert type(logger1) == type(logger2)

        # Just verify the loggers exist and are the same type
        assert hasattr(logger1, "info")
        assert hasattr(logger2, "info")

    def test_openapi_functionality(self):
        @get("/test", tags=["test"])
        async def handler() -> dict[str, str]:
            return {"test": "openapi"}

        config = AppConfig(route_handlers=[handler])
        app1 = Litestar.from_config(config)

        app2 = Litestar(route_handlers=[handler])

        with TestClient(app1) as client1, TestClient(app2) as client2:
            response1 = client1.get("/schema/openapi.json")
            response2 = client2.get("/schema/openapi.json")

            assert response1.status_code == response2.status_code == 200

            schema1 = response1.json()
            schema2 = response2.json()

            assert schema1["openapi"] == schema2["openapi"]
            assert schema1["info"]["title"] == schema2["info"]["title"] == "Litestar API"
            assert schema1["info"]["version"] == schema2["info"]["version"] == "1.0.0"
            assert "/test" in schema1["paths"]
            assert "/test" in schema2["paths"]

    def test_request_body_size_limits(self):
        @post("/upload")
        async def upload_handler(data: dict) -> dict[str, str]:
            return {"status": "success", "data": str(data)}

        config = AppConfig(route_handlers=[upload_handler], request_max_body_size=100)
        app1 = Litestar.from_config(config)

        app2 = Litestar(route_handlers=[upload_handler], request_max_body_size=100)

        assert app1.request_max_body_size == app2.request_max_body_size == 100

        small_data = {"message": "test"}

        with TestClient(app1) as client1:
            response1 = client1.post("/upload", json=small_data)
            assert response1.status_code == 201

        with TestClient(app2) as client2:
            response2 = client2.post("/upload", json=small_data)
            assert response2.status_code == 201

    def test_response_caching(self):
        @get("/cached")
        async def cached_handler() -> dict[str, str]:
            return {"timestamp": "123456"}

        config = AppConfig(
            route_handlers=[cached_handler], response_cache_config=ResponseCacheConfig(default_expiration=60)
        )
        app1 = Litestar.from_config(config)

        app2 = Litestar(
            route_handlers=[cached_handler], response_cache_config=ResponseCacheConfig(default_expiration=60)
        )

        assert app1.response_cache_config is not None
        assert app2.response_cache_config is not None
        assert app1.response_cache_config.default_expiration == app2.response_cache_config.default_expiration == 60

        with TestClient(app1) as client1, TestClient(app2) as client2:
            response1 = client1.get("/cached")
            response2 = client2.get("/cached")

            assert response1.status_code == response2.status_code == 200
            assert response1.json() == response2.json()

    def test_middleware_compatibility(self):
        from typing import Callable

        from litestar.middleware import MiddlewareProtocol

        class CustomMiddleware(MiddlewareProtocol):
            def __init__(self, app: Callable) -> None:
                self.app = app

            async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
                if scope["type"] == "http":
                    # Add custom header
                    async def send_wrapper(message):
                        if message["type"] == "http.response.start":
                            headers = list(message.get("headers", []))
                            headers.append([b"x-custom-header", b"test-value"])
                            message["headers"] = headers
                        await send(message)

                    await self.app(scope, receive, send_wrapper)
                else:
                    await self.app(scope, receive, send)

        @get("/test")
        async def handler() -> dict[str, str]:
            return {"test": "middleware"}

        config = AppConfig(route_handlers=[handler], middleware=[CustomMiddleware])
        app1 = Litestar.from_config(config)

        app2 = Litestar(route_handlers=[handler], middleware=[CustomMiddleware])

        with TestClient(app1) as client1, TestClient(app2) as client2:
            response1 = client1.get("/test")
            response2 = client2.get("/test")

            assert response1.status_code == response2.status_code == 200
            assert response1.headers["x-custom-header"] == response2.headers["x-custom-header"] == "test-value"

    def test_exception_handlers_compatibility(self):
        from litestar import Request
        from litestar.exceptions import HTTPException
        from litestar.response import Response

        def custom_exception_handler(request: Request, exc: HTTPException) -> Response:
            return Response(content={"custom_error": True, "detail": exc.detail}, status_code=exc.status_code)

        @get("/error")
        async def error_handler() -> dict[str, str]:
            raise HTTPException(status_code=400, detail="Test error")

        config = AppConfig(route_handlers=[error_handler], exception_handlers={HTTPException: custom_exception_handler})
        app1 = Litestar.from_config(config)

        app2 = Litestar(route_handlers=[error_handler], exception_handlers={HTTPException: custom_exception_handler})

        with TestClient(app1) as client1, TestClient(app2) as client2:
            response1 = client1.get("/error")
            response2 = client2.get("/error")

            assert response1.status_code == response2.status_code == 400
            assert response1.json() == response2.json() == {"custom_error": True, "detail": "Test error"}

    def test_lifecycle_hooks_compatibility(self):
        startup_called = []
        shutdown_called = []

        async def startup_hook(app: Litestar) -> None:
            startup_called.append(True)

        async def shutdown_hook(app: Litestar) -> None:
            shutdown_called.append(True)

        config = AppConfig(on_startup=[startup_hook], on_shutdown=[shutdown_hook])
        app1 = Litestar.from_config(config)

        app2 = Litestar(on_startup=[startup_hook], on_shutdown=[shutdown_hook])

        assert len(app1.on_startup) == len(app2.on_startup) == 1
        assert len(app1.on_shutdown) == len(app2.on_shutdown) == 1

        assert app1.on_startup == app2.on_startup
        assert app1.on_shutdown == app2.on_shutdown


class TestAppConfigRealWorldScenarios:
    def test_api_with_auth_and_caching(self):
        from litestar import Controller

        class ApiController(Controller):
            path = "/api"

            @get("/users/{user_id:int}", cache=60)
            async def get_user(self, user_id: int) -> dict[str, int]:
                return {"id": user_id, "name": f"User {user_id}"}

            @post("/users")
            async def create_user(self, data: dict) -> dict[str, int]:
                return {"id": 1, **data}

        config = AppConfig(
            route_handlers=[ApiController],
            response_cache_config=ResponseCacheConfig(default_expiration=120),
            openapi_config=OpenAPIConfig(title="User API", version="1.0.0", description="A simple user management API"),
        )
        app1 = Litestar.from_config(config)

        app2 = Litestar(
            route_handlers=[ApiController],
            response_cache_config=ResponseCacheConfig(default_expiration=120),
            openapi_config=OpenAPIConfig(title="User API", version="1.0.0", description="A simple user management API"),
        )

        with TestClient(app1) as client1, TestClient(app2) as client2:
            response1 = client1.get("/api/users/1")
            response2 = client2.get("/api/users/1")

            assert response1.status_code == response2.status_code == 200
            assert response1.json() == response2.json()

            user_data = {"name": "John Doe"}
            response1 = client1.post("/api/users", json=user_data)
            response2 = client2.post("/api/users", json=user_data)

            assert response1.status_code == response2.status_code == 201  # 201 for POST is correct
            assert response1.json() == response2.json()

            response1 = client1.get("/schema/openapi.json")
            response2 = client2.get("/schema/openapi.json")

            assert response1.status_code == response2.status_code == 200
            schema1 = response1.json()
            schema2 = response2.json()
            assert schema1["info"]["title"] == schema2["info"]["title"] == "User API"

    def test_debug_mode_consistency(self):
        @get("/error")
        async def error_handler() -> dict[str, str]:
            raise ValueError("Test error")

        config = AppConfig(route_handlers=[error_handler], debug=True)
        app1 = Litestar.from_config(config)

        app2 = Litestar(route_handlers=[error_handler], debug=True)

        assert app1.debug is app2.debug is True

        with TestClient(app1) as client1, TestClient(app2) as client2:
            response1 = client1.get("/error")
            response2 = client2.get("/error")

            assert response1.status_code == response2.status_code == 500

        config = AppConfig(route_handlers=[error_handler], debug=False)
        app3 = Litestar.from_config(config)

        app4 = Litestar(route_handlers=[error_handler], debug=False)

        assert app3.debug is app4.debug is False

        with TestClient(app3) as client3, TestClient(app4) as client4:
            response3 = client3.get("/error")
            response4 = client4.get("/error")

            assert response3.status_code == response4.status_code == 500
