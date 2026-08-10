from types import SimpleNamespace

import app


def test_server_has_bounded_graceful_shutdown(monkeypatch):
    options = {}

    def capture_run(application, **kwargs):
        options["application"] = application
        options.update(kwargs)

    monkeypatch.setattr(app.uvicorn, "run", capture_run)
    args = SimpleNamespace(mock=True, host="127.0.0.1", port=8000, reload=False)

    app.run_server(args)

    assert options["application"] == "app:app"
    assert options["timeout_graceful_shutdown"] == 1
