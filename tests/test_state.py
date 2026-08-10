import asyncio

import pytest

from hardware import create_hardware
from state import MotorBusyError, TrainState


@pytest.fixture
def train():
    hardware = create_hardware(mock=True)
    yield TrainState(hardware)
    hardware.close()


def test_listener_gets_initial_and_changed_state(train):
    async def scenario():
        listener = await train.add_listener()
        initial = listener.get_nowait()
        assert initial["revision"] == 0
        assert initial["led"]["on"] is False

        await train.toggle_led()
        changed = listener.get_nowait()
        assert changed["revision"] == 1
        assert changed["led"]["on"] is True

        await train.remove_listener(listener)

    asyncio.run(scenario())


def test_listener_keeps_only_newest_state(train):
    async def scenario():
        listener = await train.add_listener()
        await train.toggle_led()
        await train.toggle_led()

        assert listener.qsize() == 1
        newest = listener.get_nowait()
        assert newest["revision"] == 2
        assert newest["led"]["on"] is False

    asyncio.run(scenario())


def test_motor_owner_blocks_other_browser(train):
    async def scenario():
        await train.start_motor("first", "forward")

        with pytest.raises(MotorBusyError):
            await train.start_motor("second", "reverse")

        state = await train.snapshot()
        assert state["motor"]["direction"] == "forward"
        assert await train.motor_owner_is("first") is True

    asyncio.run(scenario())


def test_owner_release_stops_motor_and_allows_new_owner(train):
    async def scenario():
        await train.start_motor("first", "forward")
        await train.release_motor("first")

        released = await train.snapshot()
        assert released["motor"]["running"] is False
        assert released["motor"]["controlled"] is False

        claimed = await train.start_motor("second", "reverse")
        assert claimed["motor"]["direction"] == "reverse"

    asyncio.run(scenario())


def test_door_and_led_work_while_motor_owned(train):
    async def scenario():
        await train.start_motor("owner", "forward")
        closed_door = await train.toggle_door()
        open_door = await train.toggle_door()
        led = await train.toggle_led()

        assert closed_door["door"]["open"] is False
        assert open_door["door"]["open"] is True
        assert led["led"]["on"] is True
        assert led["motor"]["running"] is True

    asyncio.run(scenario())
