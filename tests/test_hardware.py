import pytest

from hardware import DOOR_CLOSED_ANGLE, DOOR_OPEN_ANGLE, create_hardware


@pytest.fixture
def hardware():
    hardware = create_hardware(mock=True)
    yield hardware
    hardware.close()


def test_mock_hardware_starts_safe(hardware):
    assert hardware.mock is True
    assert hardware.motor.pwm.value == 0
    assert hardware.motor.ain1.value == 0
    assert hardware.motor.ain2.value == 0
    assert hardware.motor.standby.value == 0
    assert hardware.door.servo.angle is None
    assert hardware.led.led.value == 0


def test_motor_moves_and_stops(hardware):
    hardware.motor.forward(0.5)
    assert hardware.motor.pwm.value == 0.5
    assert hardware.motor.ain1.value == 1
    assert hardware.motor.ain2.value == 0
    assert hardware.motor.standby.value == 1

    hardware.motor.reverse(0.75)
    assert hardware.motor.pwm.value == 0.75
    assert hardware.motor.ain1.value == 0
    assert hardware.motor.ain2.value == 1

    hardware.motor.stop()
    assert hardware.motor.pwm.value == 0
    assert hardware.motor.ain1.value == 0
    assert hardware.motor.ain2.value == 0
    assert hardware.motor.standby.value == 0


def test_motor_rejects_invalid_speed(hardware):
    with pytest.raises(ValueError, match="between 0 and 1"):
        hardware.motor.forward(1.1)


def test_door_moves_to_named_positions(hardware):
    hardware.door.open()
    assert hardware.door.servo.angle == DOOR_OPEN_ANGLE

    hardware.door.close_door()
    assert hardware.door.servo.angle == DOOR_CLOSED_ANGLE


def test_led_toggles(hardware):
    hardware.led.turn_on()
    assert hardware.led.led.value == 1

    hardware.led.turn_off()
    assert hardware.led.led.value == 0
