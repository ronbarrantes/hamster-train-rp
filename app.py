from pathlib import Path
from flask import Flask, render_template, request, jsonify


class ActLED:
    def __init__(self):
        self.trigger = Path("/sys/class/leds/ACT/trigger")
        self.brightness = Path("/sys/class/leds/ACT/brightness")
        self.trigger.write_text("none")

    def on(self):
        self.brightness.write_text("1")

    def off(self):
        self.brightness.write_text("0")

    def state(self):
        return self.brightness.read_text().strip() == "1"

    def restore(self):
        self.trigger.write_text("actpwr")


app = Flask(__name__, template_folder="ui")
led = ActLED()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/led", methods=["GET", "POST"])
def led_route():
    if request.method == "GET":
        return jsonify({"on": led.state()})

    data = request.get_json(silent=True) or {}

    if data.get("on"):
        led.on()
    else:
        led.off()

    return jsonify({"on": led.state()})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)



