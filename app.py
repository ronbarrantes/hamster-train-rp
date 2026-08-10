import argparse
import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from hardware import create_hardware
from server import router
from state import TrainState


MOCK_MODE_ENVIRONMENT_KEY = "HAMSTER_TRAIN_MOCK"
PROJECT_DIRECTORY = Path(__file__).parent
GRACEFUL_SHUTDOWN_TIMEOUT = 1


def mock_mode_enabled():
    return os.environ.get(MOCK_MODE_ENVIRONMENT_KEY) == "1"


@asynccontextmanager
async def lifespan(app):
    mock = mock_mode_enabled()
    mode_name = "MOCK GPIO" if mock else "REAL GPIO"
    print(f"Hamster Train starting with {mode_name}")

    try:
        hardware = create_hardware(mock=mock)
    except Exception as error:
        if mock:
            raise
        raise RuntimeError(
            "Could not initialize real GPIO. Ensure pigpiod is installed and running."
        ) from error

    app.state.train = TrainState(hardware)
    try:
        yield
    finally:
        await app.state.train.shutdown()
        print("Hamster Train hardware stopped")


def create_app():
    app = FastAPI(title="Hamster Train", lifespan=lifespan)
    app.mount(
        "/static",
        StaticFiles(directory=PROJECT_DIRECTORY / "static"),
        name="static",
    )
    app.include_router(router)
    return app


app = create_app()


def parse_args():
    parser = argparse.ArgumentParser(description="Run Hamster Train")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="simulate GPIO instead of connecting to Raspberry Pi hardware",
    )
    parser.add_argument("--host", default="0.0.0.0", help="address to bind")
    parser.add_argument("--port", type=int, default=8000, help="port to bind")
    parser.add_argument(
        "--reload",
        action="store_true",
        help="reload server after source changes",
    )
    return parser.parse_args()


def run_server(args):
    if args.mock:
        os.environ[MOCK_MODE_ENVIRONMENT_KEY] = "1"
    else:
        os.environ.pop(MOCK_MODE_ENVIRONMENT_KEY, None)

    uvicorn.run(
        "app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        timeout_graceful_shutdown=GRACEFUL_SHUTDOWN_TIMEOUT,
    )


if __name__ == "__main__":
    run_server(parse_args())
