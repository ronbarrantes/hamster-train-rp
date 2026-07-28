const ledButton = document.querySelector("#led-button");
const statusText = document.querySelector("#status");

function updateDisplay(isOn) {
  ledButton.classList.toggle("on", isOn);
  ledButton.classList.toggle("off", !isOn);
  ledButton.textContent = isOn ? "LED ON" : "LED OFF";
  ledButton.dataset.on = String(isOn);
  ledButton.disabled = false;

  statusText.textContent = isOn
    ? "The ACT LED is on."
    : "The ACT LED is off.";
}

async function getLedState() {
  try {
    const response = await fetch("/led");

    if (!response.ok) {
      throw new Error(`Server returned ${response.status}`);
    }

    const data = await response.json();
    updateDisplay(data.on);
  } catch (error) {
    ledButton.textContent = "Unavailable";
    statusText.textContent = error.message;
  }
}

async function toggleLed() {
  const isCurrentlyOn = ledButton.dataset.on === "true";

  ledButton.disabled = true;
  statusText.textContent = "Updating...";

  try {
    const response = await fetch("/led", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        on: !isCurrentlyOn,
      }),
    });

    if (!response.ok) {
      throw new Error(`Server returned ${response.status}`);
    }

    const data = await response.json();
    updateDisplay(data.on);
  } catch (error) {
    ledButton.disabled = false;
    statusText.textContent = error.message;
  }
}

ledButton.addEventListener("click", toggleLed);

getLedState();
