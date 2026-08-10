import asyncio
from copy import deepcopy


class MotorBusyError(Exception):
    pass


class TrainState:
    def __init__(self, hardware):
        self.hardware = hardware
        self._lock = asyncio.Lock()
        self._listeners = set()
        self._revision = 0
        self._motor_owner = None
        self._motor_direction = "stopped"
        self._motor_speed = 0.5
        # Servo starts detached, so physical door position is unknown.
        self._door_open = None
        self._led_on = False

    async def snapshot(self):
        async with self._lock:
            return self._snapshot_locked()

    async def motor_owner_is(self, owner):
        async with self._lock:
            return self._motor_owner == owner

    async def add_listener(self):
        listener = asyncio.Queue(maxsize=1)
        async with self._lock:
            self._listeners.add(listener)
            listener.put_nowait(self._snapshot_locked())
        return listener

    async def remove_listener(self, listener):
        async with self._lock:
            self._listeners.discard(listener)

    async def start_motor(self, owner, direction):
        if direction not in {"forward", "reverse"}:
            raise ValueError("Motor direction must be forward or reverse")

        async with self._lock:
            if self._motor_owner not in {None, owner}:
                raise MotorBusyError("Motor is controlled by another browser")

            if direction == "forward":
                self.hardware.motor.forward(self._motor_speed)
            else:
                self.hardware.motor.reverse(self._motor_speed)

            self._motor_owner = owner
            self._motor_direction = direction
            return self._changed_locked()

    async def set_motor_speed(self, owner, speed):
        speed = float(speed)
        if not 0 <= speed <= 1:
            raise ValueError("Motor speed must be between 0 and 1")

        async with self._lock:
            if self._motor_owner not in {None, owner}:
                raise MotorBusyError("Motor is controlled by another browser")

            self._motor_speed = speed
            if self._motor_direction != "stopped":
                self.hardware.motor.set_speed(speed)
            return self._changed_locked()

    async def stop_motor(self, owner, *, force=False):
        async with self._lock:
            if not force and self._motor_owner not in {None, owner}:
                raise MotorBusyError("Motor is controlled by another browser")

            changed = self._motor_direction != "stopped" or self._motor_owner is not None
            if changed:
                self.hardware.motor.stop()
                self._motor_direction = "stopped"
                self._motor_owner = None
                return self._changed_locked()
            return self._snapshot_locked()

    async def release_motor(self, owner):
        async with self._lock:
            if self._motor_owner != owner:
                return self._snapshot_locked()

            self.hardware.motor.stop()
            self._motor_direction = "stopped"
            self._motor_owner = None
            return self._changed_locked()

    async def toggle_door(self):
        async with self._lock:
            # First command after startup closes door and establishes known state.
            self._door_open = False if self._door_open is None else not self._door_open
            if self._door_open:
                self.hardware.door.open()
            else:
                self.hardware.door.close_door()
            return self._changed_locked()

    async def toggle_led(self):
        async with self._lock:
            self._led_on = not self._led_on
            if self._led_on:
                self.hardware.led.turn_on()
            else:
                self.hardware.led.turn_off()
            return self._changed_locked()

    async def shutdown(self):
        await self.stop_motor(None, force=True)
        self.hardware.close()

    def _changed_locked(self):
        self._revision += 1
        state = self._snapshot_locked()
        self._broadcast_locked(state)
        return state

    def _snapshot_locked(self):
        return {
            "revision": self._revision,
            "mock": self.hardware.mock,
            "motor": {
                "direction": self._motor_direction,
                "speed": self._motor_speed,
                "running": self._motor_direction != "stopped",
                "controlled": self._motor_owner is not None,
            },
            "door": {"open": self._door_open},
            "led": {"on": self._led_on},
        }

    def _broadcast_locked(self, state):
        for listener in self._listeners:
            if listener.full():
                listener.get_nowait()
            listener.put_nowait(deepcopy(state))
