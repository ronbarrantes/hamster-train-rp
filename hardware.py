from gpiozero import AngularServo, DigitalOutputDevice, LED, PWMOutputDevice
from gpiozero.pins.mock import MockFactory, MockPWMPin
from gpiozero.pins.pigpio import PiGPIOFactory


MOTOR_PWM_PIN = 17
MOTOR_AIN1_PIN = 27
MOTOR_AIN2_PIN = 22
MOTOR_STANDBY_PIN = 23
LED_PIN = 4
DOOR_SERVO_PIN = 26

DOOR_CLOSED_ANGLE = 0
DOOR_OPEN_ANGLE = 90
SERVO_MIN_ANGLE = -90
SERVO_MAX_ANGLE = 90
SERVO_MIN_PULSE_WIDTH = 0.0005
SERVO_MAX_PULSE_WIDTH = 0.0025


class Motor:
    def __init__(self, pin_factory):
        self.pwm = PWMOutputDevice(MOTOR_PWM_PIN, pin_factory=pin_factory)
        self.ain1 = DigitalOutputDevice(MOTOR_AIN1_PIN, pin_factory=pin_factory)
        self.ain2 = DigitalOutputDevice(MOTOR_AIN2_PIN, pin_factory=pin_factory)
        self.standby = DigitalOutputDevice(
            MOTOR_STANDBY_PIN,
            pin_factory=pin_factory,
        )
        self.stop()

    def forward(self, speed):
        self._move(speed, ain1_on=True, ain2_on=False)

    def reverse(self, speed):
        self._move(speed, ain1_on=False, ain2_on=True)

    def set_speed(self, speed):
        self.pwm.value = self._validate_speed(speed)

    def stop(self):
        self.pwm.value = 0
        self.ain1.off()
        self.ain2.off()
        self.standby.off()

    def close(self):
        self.stop()
        self.pwm.close()
        self.ain1.close()
        self.ain2.close()
        self.standby.close()

    def _move(self, speed, *, ain1_on, ain2_on):
        speed = self._validate_speed(speed)

        # Remove power before changing direction.
        self.pwm.value = 0
        self.ain1.value = ain1_on
        self.ain2.value = ain2_on
        self.standby.on()
        self.pwm.value = speed

    @staticmethod
    def _validate_speed(speed):
        speed = float(speed)
        if not 0 <= speed <= 1:
            raise ValueError("Motor speed must be between 0 and 1")
        return speed


class DoorServo:
    def __init__(self, pin_factory):
        self.servo = AngularServo(
            DOOR_SERVO_PIN,
            pin_factory=pin_factory,
            initial_angle=None,
            min_angle=SERVO_MIN_ANGLE,
            max_angle=SERVO_MAX_ANGLE,
            min_pulse_width=SERVO_MIN_PULSE_WIDTH,
            max_pulse_width=SERVO_MAX_PULSE_WIDTH,
        )

    def open(self):
        self.servo.angle = DOOR_OPEN_ANGLE

    def close_door(self):
        self.servo.angle = DOOR_CLOSED_ANGLE

    def close(self):
        self.servo.angle = None
        self.servo.close()


class StatusLed:
    def __init__(self, pin_factory):
        self.led = LED(LED_PIN, pin_factory=pin_factory)
        self.turn_off()

    def turn_on(self):
        self.led.on()

    def turn_off(self):
        self.led.off()

    def close(self):
        self.turn_off()
        self.led.close()


class TrainHardware:
    def __init__(self, pin_factory, *, mock):
        self.mock = mock
        self.pin_factory = pin_factory
        self.motor = None
        self.door = None
        self.led = None

        try:
            self.motor = Motor(pin_factory)
            self.door = DoorServo(pin_factory)
            self.led = StatusLed(pin_factory)
        except Exception:
            self.close()
            raise

    def close(self):
        if self.motor is not None:
            self.motor.close()
            self.motor = None
        if self.door is not None:
            self.door.close()
            self.door = None
        if self.led is not None:
            self.led.close()
            self.led = None
        self.pin_factory.close()


def create_hardware(*, mock=False):
    pin_factory = MockFactory(pin_class=MockPWMPin) if mock else PiGPIOFactory()
    return TrainHardware(pin_factory, mock=mock)
