from gpiozero import AngularServo   
from gpiozero.pins.pigpio import PiGPIOFactory
from gpiozero import LED
from time import sleep

factory = PiGPIOFactory()



led = LED(4)
servo = AngularServo(
    17,
    pin_factory=factory,
    min_angle=-90,
    max_angle=90,
    min_pulse_width=0.0005,
    max_pulse_width=0.0025,
)



for angle in (-90, 0, 90, 0):
    print(f"Moving to {angle}°")
    servo.angle = angle
    led.toggle()
    sleep(1)

servo.angle = None

print("Forward")
AIN1.on()
AIN2.off()
PWMA.value = 0.5 # 50% speed

print("Stop")
PWMA.value = 0
sleep(1)

print("Reverse")
AIN1.off()
AIN2.on()
PWMA.value = 0.5
sleep(3)

print("Stop")
PWMA.value = 0

print("Sleep")
STBY.off()

