from docs.examples.events import (
    listener_multiple_events,
    listener_multiple_listeners,
    listener_simple,
)

from litestar.status_codes import HTTP_201_CREATED
from litestar.testing import TestClient


def test_listener_receives_emitted_event() -> None:
    with TestClient(app=listener_simple.app) as client:
        response = client.post("/users", json={"first_name": "Jane", "last_name": "Doe", "email": "jane@example.com"})

        assert response.status_code == HTTP_201_CREATED

    assert listener_simple.SENT_WELCOME_EMAILS == ["jane@example.com"]


def test_listener_for_multiple_events() -> None:
    with TestClient(app=listener_multiple_events.app) as client:
        created_response = client.post("/user-created")
        password_response = client.post("/password-changed")

        assert created_response.status_code == HTTP_201_CREATED
        assert password_response.status_code == HTTP_201_CREATED

    assert listener_multiple_events.SENT_EMAILS == [
        ("jane@example.com", "Welcome aboard!"),
        ("jane@example.com", "Your password was changed."),
    ]


def test_multiple_listeners_for_same_event() -> None:
    with TestClient(app=listener_multiple_listeners.app) as client:
        response = client.post("/users", json={"email": "jane@example.com", "reason": "left the company"})

        assert response.status_code == HTTP_201_CREATED

    assert listener_multiple_listeners.SENT_FAREWELL_EMAILS == ["jane@example.com"]
    assert listener_multiple_listeners.SUPPORT_TICKETS == ["left the company"]
