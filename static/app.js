const forwardButton = document.querySelector("#forward-button");
const reverseButton = document.querySelector("#reverse-button");
const speedSlider = document.querySelector("#speed-slider");
const speedOutput = document.querySelector("#speed-output");
const motorStatus = document.querySelector("#motor-status");
const motorMessage = document.querySelector("#motor-message");
const doorButton = document.querySelector("#door-button");
const doorStatus = document.querySelector("#door-status");
const ledButton = document.querySelector("#led-button");
const ledStatus = document.querySelector("#led-status");
const modeBadge = document.querySelector("#mode-badge");
const connectionDot = document.querySelector("#connection-dot");
const connectionStatus = document.querySelector("#connection-status");
const revisionStatus = document.querySelector("#revision-status");

let latestRevision = -1;
let motorSocket = null;
let motorSocketConnected = false;
let ownsMotor = false;
let activeDirection = null;
let reconnectDelay = 500;

function receiveState(state) {
  if (!state || state.revision < latestRevision) {
    return;
  }

  latestRevision = state.revision;
  modeBadge.hidden = !state.mock;
  updateMotor(state.motor);
  updateDoor(state.door);
  updateLed(state.led);
  revisionStatus.textContent = `State revision ${state.revision}`;
}

function updateMotor(motor) {
  const direction = motor.direction;
  motorStatus.textContent = motor.running
    ? `${capitalize(direction)} · ${Math.round(motor.speed * 100)}%`
    : "Stopped";
  motorStatus.classList.toggle("active", motor.running);

  const serverSpeed = Math.round(motor.speed * 100);
  if (document.activeElement !== speedSlider) {
    speedSlider.value = serverSpeed;
    speedOutput.value = `${serverSpeed}%`;
  }

  forwardButton.classList.toggle("active", direction === "forward");
  reverseButton.classList.toggle("active", direction === "reverse");

  if (motor.controlled && !ownsMotor) {
    motorMessage.textContent = "Motor controlled by another browser.";
  } else if (motorMessage.textContent.includes("another browser")) {
    motorMessage.textContent = "";
  }
}

function updateDoor(door) {
  const positionKnown = door.open !== null;
  doorStatus.textContent = positionKnown ? (door.open ? "Open" : "Closed") : "Unknown";
  doorStatus.classList.toggle("active", door.open);
  doorButton.textContent = !positionKnown || door.open ? "Close door" : "Open door";
  doorButton.classList.toggle("active", door.open);
  doorButton.disabled = false;
}

function updateLed(led) {
  ledStatus.textContent = led.on ? "On" : "Off";
  ledStatus.classList.toggle("active", led.on);
  ledButton.textContent = led.on ? "Turn LED off" : "Turn LED on";
  ledButton.classList.toggle("active", led.on);
  ledButton.disabled = false;
}

function connectMotorSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  motorSocket = new WebSocket(`${protocol}//${window.location.host}/ws/motor`);

  motorSocket.addEventListener("open", () => {
    motorSocketConnected = true;
    reconnectDelay = 500;
    setMotorControlsEnabled(true);
    updateConnectionStatus();
  });

  motorSocket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.type === "state") {
      ownsMotor = message.you_control_motor;
      if (!ownsMotor && activeDirection === null) {
        motorMessage.textContent = "";
      }
    } else if (message.type === "error") {
      motorMessage.textContent = message.message;
    }

    if (message.state) {
      receiveState(message.state);
    }
  });

  motorSocket.addEventListener("close", () => {
    motorSocketConnected = false;
    ownsMotor = false;
    activeDirection = null;
    setMotorControlsEnabled(false);
    updateConnectionStatus();
    window.setTimeout(connectMotorSocket, reconnectDelay);
    reconnectDelay = Math.min(reconnectDelay * 2, 5000);
  });

  motorSocket.addEventListener("error", () => {
    motorSocket.close();
  });
}

function sendMotorCommand(action, value) {
  if (!motorSocketConnected || motorSocket.readyState !== WebSocket.OPEN) {
    motorMessage.textContent = "Motor connection unavailable.";
    return false;
  }

  const command = { action };
  if (value !== undefined) {
    command.value = value;
  }
  motorSocket.send(JSON.stringify(command));
  return true;
}

function startDirection(direction, button, pointerId = null) {
  if (activeDirection !== null) {
    return;
  }
  if (!sendMotorCommand(direction)) {
    return;
  }

  activeDirection = direction;
  button.classList.add("pressed");
  if (pointerId !== null) {
    button.setPointerCapture(pointerId);
  }
}

function stopDirection(button) {
  if (activeDirection === null) {
    return;
  }
  activeDirection = null;
  button.classList.remove("pressed");
  sendMotorCommand("stop");
}

function bindDirectionButton(button, direction) {
  button.addEventListener("pointerdown", (event) => {
    event.preventDefault();
    startDirection(direction, button, event.pointerId);
  });
  button.addEventListener("pointerup", () => stopDirection(button));
  button.addEventListener("pointercancel", () => stopDirection(button));
  button.addEventListener("lostpointercapture", () => stopDirection(button));

  button.addEventListener("keydown", (event) => {
    if ((event.key === " " || event.key === "Enter") && !event.repeat) {
      event.preventDefault();
      startDirection(direction, button);
    }
  });
  button.addEventListener("keyup", (event) => {
    if (event.key === " " || event.key === "Enter") {
      event.preventDefault();
      stopDirection(button);
    }
  });
}

function stopActiveDirection() {
  if (activeDirection === "forward") {
    stopDirection(forwardButton);
  } else if (activeDirection === "reverse") {
    stopDirection(reverseButton);
  }
}

function setMotorControlsEnabled(enabled) {
  forwardButton.disabled = !enabled;
  reverseButton.disabled = !enabled;
  speedSlider.disabled = !enabled;
}

async function toggleDevice(path, button) {
  button.disabled = true;
  try {
    const response = await fetch(path, { method: "POST" });
    if (!response.ok) {
      throw new Error(`Server returned ${response.status}`);
    }
    receiveState(await response.json());
  } catch (error) {
    connectionStatus.textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

function updateConnectionStatus() {
  const sseConnected = connectionDot.classList.contains("connected");
  const connected = sseConnected && motorSocketConnected;
  connectionStatus.textContent = connected ? "Connected" : "Reconnecting...";
  connectionDot.classList.toggle("ready", connected);
}

function capitalize(value) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

bindDirectionButton(forwardButton, "forward");
bindDirectionButton(reverseButton, "reverse");

speedSlider.addEventListener("input", () => {
  speedOutput.value = `${speedSlider.value}%`;
  sendMotorCommand("speed", Number(speedSlider.value) / 100);
});

doorButton.addEventListener("click", () => {
  toggleDevice("/api/door/toggle", doorButton);
});

ledButton.addEventListener("click", () => {
  toggleDevice("/api/led/toggle", ledButton);
});

window.addEventListener("blur", stopActiveDirection);
document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    stopActiveDirection();
  }
});

const events = new EventSource("/events");
events.onopen = () => {
  connectionDot.classList.add("connected");
  updateConnectionStatus();
};
events.onmessage = (event) => receiveState(JSON.parse(event.data));
events.onerror = () => {
  connectionDot.classList.remove("connected", "ready");
  updateConnectionStatus();
};

window.setInterval(() => {
  if (motorSocketConnected) {
    sendMotorCommand("heartbeat");
  }
}, 2000);
connectMotorSocket();
