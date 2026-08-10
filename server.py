import asyncio
import json
from pathlib import Path
from secrets import token_urlsafe

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates

from state import MotorBusyError


MOTOR_HEARTBEAT_TIMEOUT = 5
SSE_HEARTBEAT_INTERVAL = 15

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent / "ui")


@router.get("/")
async def home(request: Request):
    return templates.TemplateResponse(request, "index.html")


@router.get("/api/state")
async def get_state(request: Request):
    return await request.app.state.train.snapshot()


@router.post("/api/door/toggle")
async def toggle_door(request: Request):
    return await request.app.state.train.toggle_door()


@router.post("/api/led/toggle")
async def toggle_led(request: Request):
    return await request.app.state.train.toggle_led()


@router.get("/events")
async def events(request: Request):
    train = request.app.state.train
    listener = await train.add_listener()

    async def send_events():
        try:
            while True:
                try:
                    state = await asyncio.wait_for(
                        listener.get(),
                        timeout=SSE_HEARTBEAT_INTERVAL,
                    )
                    yield f"data: {json.dumps(state)}\n\n"
                except TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            await train.remove_listener(listener)

    return StreamingResponse(
        send_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.websocket("/ws/motor")
async def motor_socket(websocket: WebSocket):
    await websocket.accept()
    train = websocket.app.state.train
    owner = token_urlsafe(16)

    await send_motor_state(websocket, train, owner)

    try:
        while True:
            try:
                message = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=MOTOR_HEARTBEAT_TIMEOUT,
                )
            except TimeoutError:
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "heartbeat_timeout",
                        "message": "Motor connection heartbeat timed out",
                    }
                )
                await websocket.close(code=1008)
                break
            except (TypeError, ValueError) as error:
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "invalid_json",
                        "message": str(error),
                    }
                )
                continue

            try:
                await handle_motor_message(train, owner, message)
                await send_motor_state(websocket, train, owner)
            except MotorBusyError as error:
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "motor_busy",
                        "message": str(error),
                        "state": await train.snapshot(),
                    }
                )
            except (TypeError, ValueError) as error:
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "invalid_command",
                        "message": str(error),
                        "state": await train.snapshot(),
                    }
                )
    except WebSocketDisconnect:
        pass
    finally:
        await train.release_motor(owner)


async def handle_motor_message(train, owner, message):
    if not isinstance(message, dict):
        raise TypeError("Motor command must be a JSON object")

    action = message.get("action")
    if action == "forward":
        await train.start_motor(owner, "forward")
    elif action == "reverse":
        await train.start_motor(owner, "reverse")
    elif action == "speed":
        if "value" not in message:
            raise ValueError("Speed command requires a value")
        if isinstance(message["value"], bool):
            raise TypeError("Motor speed must be a number")
        await train.set_motor_speed(owner, message["value"])
    elif action == "stop":
        await train.stop_motor(owner)
    elif action == "heartbeat":
        return
    else:
        raise ValueError("Unknown motor action")


async def send_motor_state(websocket, train, owner):
    state = await train.snapshot()
    await websocket.send_json(
        {
            "type": "state",
            "state": state,
            "you_control_motor": await train.motor_owner_is(owner),
        }
    )
