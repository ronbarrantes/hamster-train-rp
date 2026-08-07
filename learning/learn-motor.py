from gpiozero import PWMOutputDevice, DigitalOutputDevice, LED
from time import sleep

PWMA = PWMOutputDevice(17)
AIN1 = DigitalOutputDevice(27)
AIN2 = DigitalOutputDevice(22)
STBY = DigitalOutputDevice(23)
LED1 = LED(4)

STBY.on()

print("LED on")
LED1.on()
sleep(2)

print("LED off")
LED1.off()
sleep(2)

print("Forward")
LED1.on()
AIN1.on()
AIN2.off()
PWMA.value = 0.5
sleep(3)

print("Stop")
PWMA.value = 0
LED1.off()
sleep(1)

print("Reverse")
LED1.on()
AIN1.off()
AIN2.on()
PWMA.value = 0.5
sleep(3)

print("Stop")
PWMA.value = 0
LED1.off()

STBY.off()
