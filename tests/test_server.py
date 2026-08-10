from fastapi.testclient import TestClient
import pytest

import app as app_module
import server


def test_real_mode_fails_clearly_when_gpio_is_unavailable(monkeypatch):
    monkeypatch.delenv(app_module.MOCK_MODE_ENVIRONMENT_KEY, raising=False)

    def unavailable_hardware(*, mock):
        raise OSError("pigpiod unavailable")

    monkeypatch.setattr(app_module, "create_hardware", unavailable_hardware)

    with pytest.raises(RuntimeError, match="Could not initialize real GPIO"):
        with TestClient(app_module.app):
            pass


def test_rest_controls_and_mock_mode(monkeypatch):
    monkeypatch.setenv(app_module.MOCK_MODE_ENVIRONMENT_KEY, "1")

    with TestClient(app_module.app) as client:
        initial = client.get("/api/state")
        assert initial.status_code == 200
        assert initial.json()["mock"] is True

        closed_door = client.post("/api/door/toggle").json()
        open_door = client.post("/api/door/toggle").json()
        led = client.post("/api/led/toggle").json()
        assert closed_door["door"]["open"] is False
        assert open_door["door"]["open"] is True
        assert led["led"]["on"] is True


def test_motor_websocket_ownership_and_disconnect_cleanup(monkeypatch):
    monkeypatch.setenv(app_module.MOCK_MODE_ENVIRONMENT_KEY, "1")

    with TestClient(app_module.app) as client:
        with client.websocket_connect("/ws/motor") as first:
            assert first.receive_json()["state"]["motor"]["running"] is False
            first.send_json({"action": "forward"})
            claimed = first.receive_json()
            assert claimed["you_control_motor"] is True
            assert claimed["state"]["motor"]["direction"] == "forward"

            with client.websocket_connect("/ws/motor") as second:
                assert second.receive_json()["you_control_motor"] is False
                second.send_json({"action": "reverse"})
                rejected = second.receive_json()
                assert rejected["code"] == "motor_busy"

        state = client.get("/api/state").json()
        assert state["motor"]["running"] is False
        assert state["motor"]["controlled"] is False


def test_motor_websocket_validates_commands(monkeypatch):
    monkeypatch.setenv(app_module.MOCK_MODE_ENVIRONMENT_KEY, "1")

    with TestClient(app_module.app) as client:
        with client.websocket_connect("/ws/motor") as socket:
            socket.receive_json()

            socket.send_json({"action": "speed", "value": 2})
            assert socket.receive_json()["code"] == "invalid_command"

            socket.send_json({"action": "launch"})
            assert socket.receive_json()["code"] == "invalid_command"


def test_motor_heartbeat_timeout_releases_owner(monkeypatch):
    monkeypatch.setenv(app_module.MOCK_MODE_ENVIRONMENT_KEY, "1")
    monkeypatch.setattr(server, "MOTOR_HEARTBEAT_TIMEOUT", 0.05)

    with TestClient(app_module.app) as client:
        with client.websocket_connect("/ws/motor") as socket:
            socket.receive_json()
            socket.send_json({"action": "forward"})
            assert socket.receive_json()["you_control_motor"] is True
            assert socket.receive_json()["code"] == "heartbeat_timeout"

        state = client.get("/api/state").json()
        assert state["motor"]["running"] is False
        assert state["motor"]["controlled"] is False


def test_dashboard_and_static_files_are_served(monkeypatch):
    monkeypatch.setenv(app_module.MOCK_MODE_ENVIRONMENT_KEY, "1")

    with TestClient(app_module.app) as client:
        page = client.get("/")
        script = client.get("/static/app.js")

        assert page.status_code == 200
        assert "Hamster Train" in page.text
        assert "Forward" in page.text
        assert script.status_code == 200
        assert 'new EventSource("/events")' in script.text
