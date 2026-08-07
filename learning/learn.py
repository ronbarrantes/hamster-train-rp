from gpiozero import LED
from gpiozero import AngularServo
from time import sleep

led = None
servo = None

def setup():
    global led   
    led = LED(4)
    servo = AngularServo(
        17,
        min_angle=-90,
        max_angle=90,
        min_pulse_width=0.0005,
        max_pulse_width=0.0025,
    )



def loop():
    led.toggle()
    sleep(.01)


def main():
    setup()
    while True:
        loop()


if __name__ == "__main__":
    main()

