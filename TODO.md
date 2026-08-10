# Hamster Train TODO

## Application structure

- [x] Keep `app.py` small: CLI flags, FastAPI creation, startup, shutdown
- [x] Add `server.py` for HTML, REST, SSE, and WebSocket routes
- [x] Add `hardware.py` for motor, door servo, and LED control
- [x] Add `state.py` for shared state, revisions, subscribers, and motor ownership
- [x] Remove all ACT LED behavior

## GPIO hardware

- [x] Configure motor PWM on GPIO 17
- [x] Configure motor direction pins on GPIO 27 and GPIO 22
- [x] Configure motor standby on GPIO 23
- [x] Configure external LED on GPIO 4
- [x] Configure door servo on GPIO 26
- [x] Add readable `Motor`, `DoorServo`, and `StatusLed` classes
- [x] Add named, easy-to-calibrate servo open and closed angles
- [x] Stop and release all hardware safely during shutdown or failure

## Real and mock modes

- [x] Use real GPIO by default
- [x] Add `--mock` CLI flag using GPIO Zero `MockFactory`
- [x] Add `--host`, `--port`, and `--reload` CLI options
- [x] Show active hardware mode in terminal and dashboard
- [x] Fail clearly when real mode cannot connect to `pigpiod`
- [x] Never silently switch from real mode to mock mode

## Shared state and SSE

- [x] Define complete motor, door, LED, revision, and mock-mode state
- [x] Protect concurrent state changes with a lock
- [x] Add `GET /api/state`
- [x] Add `GET /events` SSE stream
- [x] Send complete state immediately when browser connects
- [x] Broadcast complete state after every successful change
- [x] Keep only newest queued update per browser
- [x] Add SSE heartbeat and disconnected-subscriber cleanup

## Motor WebSocket

- [x] Add `WS /ws/motor`
- [x] Support forward, reverse, speed, stop, and heartbeat messages
- [x] Validate message shape and speed range
- [x] Claim ownership only when movement starts
- [x] Prevent non-owner direction and live-speed changes
- [x] Allow any browser to set speed while motor is idle and unowned
- [x] Stop motor and release ownership on owner Stop
- [x] Stop motor and release ownership on owner disconnect
- [x] Add heartbeat watchdog for stale connections
- [x] Clear stale ownership on timeout and application shutdown
- [x] Prevent ownership races between browsers

## REST controls

- [x] Add `POST /api/door/toggle`
- [x] Add `POST /api/led/toggle`
- [x] Keep door and LED usable while another browser owns motor
- [x] Return updated authoritative state from successful commands

## Dashboard

- [x] Replace ACT LED interface with three device controllers
- [x] Add hold-to-run Forward and Reverse motor buttons
- [x] Add motor speed slider
- [x] Handle mouse, touch, stylus, cancellation, and release safely
- [x] Show motor direction, speed, and ownership status
- [x] Add one Open/Close door button
- [x] Show current door state
- [x] Add one LED On/Off button
- [x] Show current LED state
- [x] Connect motor controls through WebSocket
- [x] Connect door and LED controls through REST
- [x] Synchronize all controls through SSE
- [x] Show connection loss and simulation-mode status clearly

## Tests and documentation

- [x] Test hardware behavior with mock GPIO
- [x] Test REST state changes
- [x] Test WebSocket commands and validation
- [x] Test two-browser motor ownership
- [x] Test disconnect and watchdog cleanup
- [x] Test SSE initial state and broadcasts
- [x] Test safe application shutdown
- [ ] Visually verify full dashboard in a browser on macOS with `--mock`
- [ ] Verify real GPIO behavior on Raspberry Pi Zero W
- [x] Update `README.md` with setup, commands, and `pigpiod` requirements
- [x] Update `HARDWARE_PLAN.md` to describe FastAPI and external GPIO devices
