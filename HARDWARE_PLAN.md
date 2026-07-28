# Hamster Train: Software and Hardware Plan

This document summarizes the decisions and ideas discussed while building the
Hamster Train project. It is written for a software developer who is new to
electronics.

## Current project

The current system runs on a Raspberry Pi Zero W:

- Flask serves the dashboard on port `5000`.
- The browser sends commands with normal HTTP requests.
- Server-Sent Events (SSE) push state changes to every connected browser.
- The Raspberry Pi ACT LED is the temporary output device.
- The LED starts off to indicate that the application is ready.
- Two browsers can control the LED and remain synchronized.

Set `User` to the deployment account. The systemd service uses `%h`, that
account's home directory, so the same layout also works when the account is
`root`:

```ini
User=<deployment-account>
WorkingDirectory=%h/application/hamster-train-rp
ExecStart=%h/application/hamster-train-rp/.venv/bin/python \
    %h/application/hamster-train-rp/app.py
```

Normal startup listens on `0.0.0.0` so trusted home-network and WireGuard
devices can connect without extra service arguments.

Debug mode is off by default. Development mode can be enabled with:

```bash
python app.py --debug
```

Flask's automatic reloader remains disabled because it can start the
application twice and initialize hardware twice.

## Current ACT LED behavior

The Pi Zero W ACT LED has unusual values:

| Operation or state | Value |
|---|---:|
| Write to turn LED on | `1` |
| Read while LED is on | `255` |
| Write to turn LED off | `0` |
| Read while LED is off | `0` |

Therefore, the application treats any nonzero brightness as on.

The selected trigger is currently:

```text
[none]
```

The brackets show the active trigger. Other trigger names are available
choices; they are not all active at once.

Long term, the ACT LED may become a system status indicator:

- Off: application ready and idle.
- Short blink: command received.
- On while busy: motor, sound, or lighting action is running.
- Steady on: problem.

The Linux `oneshot` trigger may eventually handle short command flashes. The
ACT LED could move into a separate Bash or Python systemd service so the main
application can focus on GPIO devices.

## Browser state synchronization

SSE is used for one-way server-to-browser updates:

```text
Browser command ──HTTP POST──> Flask
                                │
Hardware input ────────────────>│
                                │
                                └──SSE state──> every browser
```

Current routes:

| Route | Purpose |
|---|---|
| `GET /` | Dashboard |
| `GET /led` | Current LED state |
| `POST /led/toggle` | Toggle LED on the server |
| `GET /events` | SSE state stream |

Important implementation ideas:

- Toggle logic runs on the server. Browsers do not guess the next state.
- A lock allows only one hardware change at a time.
- Each browser gets a one-message queue, like a mailbox.
- Only the newest state matters.
- A revision number prevents old responses from replacing newer state.
- A heartbeat is sent every 15 seconds to keep quiet SSE connections alive.
- A disconnected browser's queue is removed.
- New connections immediately receive the current state.

Redis is not needed. One Flask process can keep live state and SSE subscribers
in memory. Redis becomes useful only if multiple processes or computers must
share state and broadcast events.

SQLite may eventually store settings or history. It should not be used as a
message bus between services.

## Future software separation

Possible long-term service layout:

```text
hamster-train.service
  Flask
  SSE
  GPIO buttons and outputs
  motor control
  servo control
  sound
  camera

hamster-led.service
  onboard ACT LED only
  ready, activity, and failure patterns
```

The dashboard already knows when it starts a motor, changes an RGB light, or
plays a sound. It can broadcast that state directly through SSE. The ACT LED
service does not need to report its state back to the dashboard.

If Flask crashes, SSE also stops. Systemd can tell the separate ACT LED service
to display a failure state. When Flask restarts, browsers reconnect and receive
a new complete state snapshot.

## Developing without a Raspberry Pi

GPIO Zero includes an official fake pin implementation:

```bash
GPIOZERO_PIN_FACTORY=mock python app.py --debug
```

This can simulate GPIO LEDs, buttons, PWM, and connected pins on a Mac without
SSH or a Raspberry Pi.

The current application still accesses the special ACT LED through
`/sys/class/leds/ACT`, so it cannot yet run unchanged on a Mac. There is no
urgent need to refactor it. Later:

1. Remove ACT LED control from the Flask application.
2. Move ACT behavior into its own Pi-only service.
3. Use GPIO Zero for external devices.
4. Use GPIO Zero's mock pin factory on the Mac.

The Flask, SSE, dashboard, and state-management code can stay the same in both
environments.

## Camera

Planned camera:

- Arducam 5MP camera
- OmniVision OV5647 sensor
- Raspberry Pi Camera Module V1 compatible
- Fixed focus

The OV5647 is supported by the current Raspberry Pi `libcamera`/`rpicam`
software stack.

The Pi Zero W uses a narrow 22-pin camera connector. The camera uses a standard
15-pin connector, so use the included 15-to-22-pin ribbon cable.

Always shut down and remove power before connecting or disconnecting the
camera.

Test camera detection with:

```bash
rpicam-hello --list-cameras
```

Test a still image with:

```bash
rpicam-still -o test.jpg
```

### Initial streaming plan

Camera streaming can remain on port `5000`:

| Route | Purpose |
|---|---|
| `/` | Dashboard |
| `/events` | SSE state |
| `/camera.mjpg` | MJPEG camera stream |

Video does not travel through SSE. It uses its own long-running HTTP response.

Initial target for the original Zero W:

- 640x480
- 10 frames per second
- One camera capture process
- One shared latest-frame buffer
- One or two viewers
- No OpenCV processing
- No separate encoder per viewer

Picamera2 should open the camera once. Every browser shares frames from that
single capture.

If MJPEG later uses too much bandwidth or CPU, MediaMTX can provide H.264,
WebRTC, RTSP, audio, recording, and better support for many viewers. It is not
needed for the first version.

## Planned hardware

| Device | Pi's job | Required interface hardware |
|---|---|---|
| Camera | Configure and stream | CSI ribbon cable |
| DC motor | Direction and speed signals | TB6612FNG motor driver |
| Servo | Position signal | External power; possibly PCA9685 |
| LEDs | On/off or brightness signals | Current-limiting resistor or LED driver |
| Speaker | Audio/control signal | Powered amplifier |
| Pressure plate | Read open/closed contact | Pull-up input and debounce |

The Pi is the brain. It should send low-current control signals. Driver boards
and external supplies provide power.

## Breadboard prototyping

A breadboard is a good way to build the first version without making every
connection permanent.

Good breadboard uses:

- GPIO control signals
- LEDs and current-limiting resistors
- Pressure plate input
- TB6612FNG logic connections
- MAX98357A digital audio connections
- Low-current common-ground connections

Do not route motor or servo power through breadboard rails. Breadboard contacts
and thin jumper wires are not dependable for high current. Run external power
directly to the motor driver and servo using suitable wire:

```text
External power ──direct wire──> motor driver and servo
Pi GPIO ─────────breadboard───> control pins
Grounds ──────────────────────> connected together
```

Common breadboard traps:

- Long red and blue power rails may be split in the middle.
- Left and right power rails are usually separate.
- Rail colors are labels only; they do not provide voltage.
- A jumper can look connected while sitting in the wrong row.
- Loose jumpers cause intermittent and confusing behavior.
- Mixing 5V and 3.3V rails can damage GPIO.
- Rewiring while powered can create accidental shorts.

Before connecting the Pi:

1. Disconnect all power.
2. Use multimeter continuity mode to map each power rail.
3. Label the 5V, 3.3V, and ground rails.
4. Check that 5V and ground are not shorted.
5. Apply power and use DC voltage mode to verify each rail.
6. Remove power again before connecting devices.

Avoid multimeter current mode until it is specifically needed. Connecting a
meter in current mode directly across a battery or power rail creates a short.

## TB6612FNG motor driver

The TB6612FNG is a dual brushed-DC-motor driver.

Conceptual wiring for one motor:

```text
Pi 3.3V ────────> VCC
Motor supply ───> VM
Pi GPIO ────────> AIN1
Pi GPIO ────────> AIN2
Pi PWM GPIO ────> PWMA
Pi GPIO ────────> STBY
Motor ──────────> AO1 and AO2
All grounds ────> common ground
```

Relevant operating limits:

- Logic supply (`VCC`): 2.7V to 5.5V. Pi 3.3V logic is suitable.
- Motor supply (`VM`): 2.5V to 13.5V.
- Approximately 1A continuous per channel when `VM` is at least 4.5V.
- Peak-current ratings apply only for short periods.

The motor's stall current must fit within the driver's safe current range.
Stall current is the current drawn when power is applied but the shaft cannot
turn. It is usually much higher than normal running current.

Never connect a motor directly to a GPIO pin.

Place power-supply capacitors near the motor driver. A small capacitor across
the motor terminals may also reduce electrical noise.

## Servo

The Pi supplies only the servo control signal. The servo receives power from an
external regulated supply.

```text
Pi GPIO ─────────> servo signal
External 5V ─────> servo power
Common ground ───> Pi, servo, and external supply
```

Servos can draw large current spikes when starting, stopping, or stalled. Those
spikes can reboot the Pi if the servo shares a weak power path with it.

Camera and web-server load may also make software-generated servo timing
jitter. A PCA9685 I2C PWM controller is a possible later upgrade for stable
servo and LED PWM.

## LEDs

A normal LED needs a series resistor to limit current. Do not connect an LED
directly between GPIO and ground without a resistor.

Multiple normal LEDs may use one GPIO per LED. Addressable RGB LEDs can use
fewer GPIO pins but may require a 3.3V-to-5V level shifter and a separate 5V
power supply.

Exact LED wiring depends on the selected LED type.

## Speaker

A conventional speaker must not be driven directly from GPIO. Use a powered
amplifier appropriate for the speaker.

The Pi Zero W has no normal analog headphone output. Possible future audio
options include:

- PWM audio plus filtering and amplification
- I2S digital amplifier
- USB audio adapter
- Powered buzzer for simple tones

Select the speaker and amplifier before assigning pins.

## Pressure plate

The proposed pressure plate is a simple switch: two plates or wires touch each
other.

Safe basic arrangement:

```text
GPIO input with pull-up ──> first plate
Ground ───────────────────> second plate
```

When open, the input reads high. When the plates touch, the input connects to
ground and reads low.

Do not place 5V across the plates.

Mechanical contacts bounce: they may rapidly connect and disconnect for a few
milliseconds during one press. Software debounce treats those rapid changes as
one event.

Long exposed wires may collect electrical noise or static. Final wiring may
need an external resistor, filtering, and protection depending on wire length
and environment.

## Power architecture

Start with a commercial USB-C power bank. It is enclosed, rechargeable, and
includes professionally designed cell protection.

Suggested class:

- 10,000mAh
- 20W to 30W wired output
- At least two wired output ports
- Near 4A or more total at 5V
- Short-circuit, overcurrent, and temperature protection
- Reputable manufacturer
- Around 200g, if train weight permits

Example discussed: Anker Nano Power Bank 10K 30W, model A1259. Its published
multi-port rating is 24W total and 5V/4.8A total.

The exact power bank cannot be finalized until motor and servo stall currents
are known.

### Power distribution

```text
USB-C power bank
        │
        ├── clean 5V branch ──> Pi Zero W and camera
        │
        └── high-current branch
              ├── TB6612FNG motor supply
              ├── servo supply
              └── speaker amplifier

All grounds connected
```

Use separate power wires or branches even when one battery powers everything.
This helps keep motor and servo noise away from the Pi.

Treat the A1259's ports as one shared 5V/4.8A source, not as independent
supplies. A preliminary simultaneous-peak budget for selecting parts is:

| Load | Startup/stall allocation |
|---|---:|
| Pi Zero W and camera | 1.2A startup/peak reserve |
| One motor through the TB6612FNG | 1.0A stall maximum |
| Servo or servos combined | 1.2A stall maximum |
| Speaker amplifier | 0.8A peak at maximum intended volume |
| **Combined peak** | **4.2A** |

The 4.2A total leaves 0.6A below the bank's shared 4.8A rating for conversion
and wiring margin. These are selection ceilings, not assumed device currents:
replace them with measured startup, motor-stall, combined servo-stall, and
maximum-volume amplifier input currents. If any load exceeds its allocation,
recalculate the total rather than borrowing the margin.

At a 5V motor supply, design for no more than about 1A sustained on one
TB6612FNG channel. Its higher peak rating is a brief pulse rating, not
permission for a motor that draws more than 1A while stalled. Select a motor
whose measured stall current fits both that operating limit and the power
budget.

Separate wires reduce shared wiring impedance and noise, but separate power-bank
ports do not prove that the branches are safe. With the final cables and all
loads attached, measure voltage at the Pi, motor driver, servo supply, and
amplifier during Pi startup and a brief, controlled simultaneous motor/servo
stall test plus loud audio. Repeat for every intended port assignment and at
low battery charge. Do not accept the layout if the combined peak exceeds
4.8A, the Pi rail falls below 4.75V, or any other rail falls outside its
device's specified input range. Also confirm that the bank neither shuts down
nor repeatedly reconnects.

Add a fuse and main switch to the peripheral power branch. Final fuse size
depends on measured current.

Do not use a rectangular 9V battery for this load. It has poor current
capability for motors and servos and will suffer voltage drop and short runtime.

## Possible future internal USB-C battery

A polished later version could have an internal rechargeable battery and USB-C
charging port:

```text
USB-C input
    ↓
1S charger with power-path/load sharing
    ↓
Protected internal 1S LiPo pack
    ↓
5V boost regulator
    ├── Pi and camera
    └── motor, servo, and speaker branches
```

One-cell (`1S`) lithium battery voltage:

- 4.2V fully charged
- About 3.7V nominal
- Near 3.0V discharged

The Pi requires a stable 5V supply, so a 1S battery requires a boost regulator.

Important terms:

- **Battery protection/BMS:** disconnects the battery during unsafe
  overcharge, over-discharge, overcurrent, or short-circuit conditions.
- **Charger:** charges the correct battery chemistry and cell count.
- **Power path/load sharing:** powers the project while charging and switches
  smoothly between charger and battery.
- **Boost converter:** raises voltage, such as 3.7V to 5V.
- **Buck converter:** lowers voltage.

A BMS is not automatically a charger. A basic 1S charger must never charge a
2S battery.

Avoid building a pack from loose lithium cells. A safer custom build uses a
preassembled protected battery pack, matched charger/power-path module, fuse,
switch, regulators, connectors, strain relief, and a proper enclosure.

Battery assembly and charging are adult tasks.

## Essential electrical rules

1. Raspberry Pi GPIO uses 3.3V logic and is not 5V tolerant.
2. Never power motors, servos, or conventional speakers from GPIO.
3. Use a current-limiting resistor with each normal LED.
4. External control circuits normally need a common ground with the Pi.
5. Check motor and servo stall current, not only normal running current.
6. Disconnect power before changing camera or power wiring.
7. Use fuses, switches, insulation, strain relief, and enclosures.
8. Keep moving motor and train parts away from fingers.
9. Shut the Pi down cleanly before removing power to reduce SD-card corruption.
10. Test one new device at a time.
11. Do not carry motor or servo current through breadboard rails.

## Hardware glossary for software developers

### GPIO

General-purpose input/output pin. Software can read a digital high/low value or
set an output high/low.

### PWM

Pulse-width modulation. A digital output switches rapidly. Changing the
percentage of on-time controls apparent LED brightness, motor speed, or servo
position signals.

### CSI

Camera Serial Interface. The dedicated ribbon-cable connection used by the Pi
camera.

### H-bridge

Motor-driver circuit that can send current through a motor in either direction.
The TB6612FNG contains two H-bridges.

### Pull-up resistor

A weak connection to 3.3V that gives an input a known high state when no switch
is connected. A switch can safely pull that input to ground.

### Debounce

Filtering rapid electrical changes from a mechanical switch so one physical
press produces one software event.

### Common ground

Connected ground/reference between the Pi and externally powered control
circuits. Without a shared reference, a 3.3V control signal may have no clear
meaning to the receiving circuit.

### Stall current

Maximum motor or servo current when commanded to move but physically unable to
move.

### Decoupling or bulk capacitor

Temporary local energy storage that reduces voltage dips and electrical noise.

### BMS

Battery Management System. Protects a battery pack and may balance cells. It
does not necessarily charge the battery.

### Power-path controller

Chooses safely between external power and battery power while allowing a
device to keep running during charging or unplugging.

## Information needed before final wiring

- Exact DC motor model
- Motor operating voltage
- Motor running current
- Motor stall current
- Number of motors
- Exact servo model and stall current
- LED types and quantities
- Speaker type and amplifier
- Desired train runtime
- Available physical space and weight limit
- Whether charging while running is required

## Suggested build order

1. Keep current ACT LED and SSE demo working.
2. Connect and test the OV5647 camera.
3. Add low-resolution MJPEG streaming.
4. Establish GPIO Zero mock development on the Mac.
5. Test a normal external LED with a resistor.
6. Test the pressure plate as a debounced button.
7. Test the servo with external power.
8. Test the motor through the TB6612FNG with wheels raised.
9. Add speaker and amplifier.
10. Combine devices using a commercial power bank.
11. Measure peak current and runtime.
12. Consider an internal USB-C battery system.
13. Move ACT LED status into a separate Pi-only service.

## References

- [Raspberry Pi GPIO and hardware documentation](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html)
- [Raspberry Pi camera hardware guide](https://www.raspberrypi.com/documentation/accessories/camera.html)
- [Raspberry Pi camera software guide](https://www.raspberrypi.com/documentation/computers/camera_software.html)
- [Picamera2 manual](https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf)
- [GPIO Zero mock pin documentation](https://gpiozero.readthedocs.io/en/stable/api_pins.html)
- [Linux LED trigger documentation](https://docs.kernel.org/leds/leds-class.html)
- [Linux one-shot LED trigger documentation](https://www.kernel.org/doc/html/next/leds/ledtrig-oneshot.html)
- [Toshiba TB6612FNG datasheet](https://toshiba.semicon-storage.com/info/datasheet_en_20141001.pdf?did=10660)
- [CPSC loose lithium-cell warning](https://www.cpsc.gov/Newsroom/News-Releases/2021/CPSC-Issues-Consumer-Safety-Warning-Serious-Injury-or-Death-Can-Occur-if-Lithium-Ion-Battery-Cells-Are-Separated-from-Battery-Packs-and-Used-to-Power-Devices)
