const ledButton = document.querySelector("#led-button");
const statusText = document.querySelector("#status");
let latestRevision = -1;

function updateDisplay(isOn) {
  ledButton.classList.toggle("on", isOn);
  ledButton.classList.toggle("off", !isOn);
  ledButton.textContent = isOn ? "LED ON" : "LED OFF";
  ledButton.disabled = false;

  statusText.textContent = isOn
    ? "The ACT LED is on."
    : "The ACT LED is off.";
}

function receiveState(state) {
  if (state.revision < latestRevision) {
    return;
  }

  latestRevision = state.revision;
  updateDisplay(state.on);
}

async function toggleLed() {
  ledButton.disabled = true;
  statusText.textContent = "Updating...";

  try {
    const response = await fetch("/led/toggle", {
      method: "POST",
    });

    if (!response.ok) {
      throw new Error(`Server returned ${response.status}`);
    }

    const data = await response.json();
    receiveState(data);
  } catch (error) {
    ledButton.disabled = false;
    statusText.textContent = error.message;
  }
}

ledButton.addEventListener("click", toggleLed);

const events = new EventSource("/events");

events.onmessage = (event) => {
  receiveState(JSON.parse(event.data));
};

events.onerror = () => {
  latestRevision = -1;
  statusText.textContent = "Connection lost. Reconnecting...";
};
