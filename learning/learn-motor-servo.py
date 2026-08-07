from gpiozero import PWMOutputDevice, DigitalOutputDevice, LED, AngularServo
from gpiozero.pins.pigpio import PiGPIOFactory
from time import sleep

factory = PiGPIOFactory()

PWMA = PWMOutputDevice(17, pin_factory=factory)
AIN1 = DigitalOutputDevice(27, pin_factory=factory)
AIN2 = DigitalOutputDevice(22, pin_factory=factory)
STBY = DigitalOutputDevice(23, pin_factory=factory)
LED1 = LED(4, pin_factory=factory)

servo = AngularServo(
    26,
    pin_factory=factory,
    min_angle=-90,
    max_angle=90,
    min_pulse_width=0.0005,
    max_pulse_width=0.0025,
)

try:
    servo.angle = None
    STBY.on()

    print("LED on")
    LED1.on()
    sleep(2)

    print("LED off")
    LED1.off()
    sleep(2)

    for angle in (-90, 0, 90, 0):
        print(f"Moving to {angle}°")
        servo.angle = angle
        LED1.toggle()
        sleep(1)

    servo.angle = None
    LED1.off()

    print("Forward")
    AIN1.on()
    AIN2.off()
    LED1.on()
    PWMA.value = 0.5
    sleep(3)

    print("Stop")
    PWMA.value = 0
    LED1.off()
    sleep(1)

    print("Reverse")
    AIN1.off()
    AIN2.on()
    LED1.on()
    PWMA.value = 0.5
    sleep(3)

finally:
    print("Stop and sleep")
    PWMA.value = 0
    AIN1.off()
    AIN2.off()
    STBY.off()
    LED1.off()
    servo.angle = None
