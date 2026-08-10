# Hamster Train

FastAPI dashboard for controlling a Raspberry Pi Zero W motor, door servo, and
external LED. Motor commands use WebSocket. REST controls door and LED. SSE
keeps every connected dashboard synchronized.

## Create virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Install test dependencies when developing:

```bash
python -m pip install -r requirements-dev.txt
```

## Run on macOS

Mock mode simulates every GPIO pin in memory. No Raspberry Pi needed.

```bash
python app.py --mock --reload
```

Open <http://127.0.0.1:8000>.

The dashboard and terminal show `Simulation mode`. Mock mode exercises REST,
SSE, WebSocket ownership, disconnect cleanup, and UI behavior without moving
physical hardware.

## Run on Raspberry Pi

Install and start the `pigpiod` daemon through Raspberry Pi OS first. Then:

```bash
python app.py
```

Real GPIO is the default. Startup fails instead of silently using mock pins when
`pigpiod` cannot be reached.

Available CLI options:

```text
--mock          use simulated GPIO
--host HOST     bind address; default 0.0.0.0
--port PORT     bind port; default 8000
--reload        reload after source changes
```

`uvicorn app:app` also runs real GPIO mode. Use one Uvicorn worker: live state,
SSE subscribers, and motor ownership belong to one process.

## GPIO pins

GPIO numbers use BCM numbering.

| Device | GPIO |
|---|---:|
| Motor PWM | 17 |
| Motor AIN1 | 27 |
| Motor AIN2 | 22 |
| Motor standby | 23 |
| External LED | 4 |
| Door servo signal | 26 |

Motor and servo power must come from suitable external supplies. Raspberry Pi,
motor driver, servo supply, and LED circuit must share a common ground. Never
power a motor or servo from GPIO.

Door angles and servo pulse widths live as named constants at the top of
`hardware.py`. Calibrate them for the installed servo and linkage before normal
use. Servo starts detached, so door position begins as unknown. First door
command closes it and establishes a known position.

## Controls and API

| Route | Purpose |
|---|---|
| `GET /` | Dashboard |
| `GET /api/state` | Complete authoritative state |
| `POST /api/door/toggle` | Open or close door |
| `POST /api/led/toggle` | Toggle external LED |
| `GET /events` | SSE state stream |
| `WS /ws/motor` | Motor commands and heartbeat |

Motor WebSocket messages:

```json
{"action": "forward"}
{"action": "reverse"}
{"action": "speed", "value": 0.5}
{"action": "stop"}
{"action": "heartbeat"}
```

First browser to start movement owns motor. Stop, disconnect, heartbeat timeout,
or application shutdown stops motor and releases ownership. Other browsers can
still control door and LED.

## Tests

```bash
python -m pytest -q
```

Tests use mock GPIO. No Raspberry Pi required.
