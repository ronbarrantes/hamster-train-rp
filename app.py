import argparse
import json
from pathlib import Path
from queue import Empty, Queue
from threading import Lock

from flask import Flask, Response, jsonify, render_template, stream_with_context


# Files used by Linux to control the Raspberry Pi ACT LED.
TRIGGER_PATH = Path("/sys/class/leds/ACT/trigger")
BRIGHTNESS_PATH = Path("/sys/class/leds/ACT/brightness")

# Only one thread may change shared LED state at a time.
led_lock = Lock()

# Each connected browser gets a queue. Think of each queue as a mailbox.
listeners = set()

# Revision is a counter. Bigger numbers mean newer state.
revision = 0


def turn_led_on():
    # Writing 1 turns this Pi's ACT LED on. It reads back as 255.
    BRIGHTNESS_PATH.write_text("1")


def turn_led_off():
    # Writing and reading 0 means off.
    BRIGHTNESS_PATH.write_text("0")


def is_led_on():
    return BRIGHTNESS_PATH.read_text().strip() != "0"


def make_state_message():
    return {
        "on": is_led_on(),
        "revision": revision,
    }


def get_state():
    with led_lock:
        return make_state_message()


def send_state_to_everyone(state):
    for listener in listeners:
        # Only newest message matters, so each mailbox holds one message.
        if listener.full():
            try:
                listener.get_nowait()
            except Empty:
                pass
        listener.put_nowait(state)


def toggle_led():
    global revision

    with led_lock:
        if is_led_on():
            turn_led_off()
        else:
            turn_led_on()

        revision += 1
        state = make_state_message()
        send_state_to_everyone(state)
        return state


def add_listener():
    listener = Queue(maxsize=1)

    with led_lock:
        listeners.add(listener)
        listener.put_nowait(make_state_message())

    return listener


def remove_listener(listener):
    with led_lock:
        listeners.discard(listener)


app = Flask(__name__, template_folder="ui")

# Take control of the ACT LED. Off means the app is ready.
TRIGGER_PATH.write_text("none")
turn_led_off()


@app.route("/")
def home():
    return render_template("index.html")


@app.get("/led")
def get_led():
    return jsonify(get_state())


@app.post("/led/toggle")
def toggle_led_route():
    return jsonify(toggle_led())


@app.get("/events")
def events():
    listener = add_listener()

    def send_events():
        try:
            while True:
                try:
                    state = listener.get(timeout=15)
                    yield f"data: {json.dumps(state)}\n\n"
                except Empty:
                    # SSE comments keep quiet connections alive.
                    yield ": heartbeat\n\n"
        finally:
            remove_listener(listener)

    return Response(
        stream_with_context(send_events()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--debug",
        action="store_true",
        help="show detailed errors while developing",
    )
    args = parser.parse_args()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=args.debug,
        use_reloader=False,
        threaded=True,
    )
