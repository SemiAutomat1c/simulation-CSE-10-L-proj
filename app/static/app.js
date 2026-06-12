const scenarioSelect = document.getElementById("scenarioSelect");
const playPauseButton = document.getElementById("playPauseButton");
const replayButton = document.getElementById("replayButton");
const slotLayer = document.getElementById("slotLayer");
const carLayer = document.getElementById("carLayer");
const entryGateArm = document.getElementById("entryGateArm");
const exitGateArm = document.getElementById("exitGateArm");
const speedSlider = document.getElementById("speedSlider");
const speedValue = document.getElementById("speedValue");
let speedMultiplier = 1.0;

const currentTime = document.getElementById("currentTime");
const entryQueue = document.getElementById("entryQueue");
const availableSlots = document.getElementById("availableSlots");
const exitQueue = document.getElementById("exitQueue");
const metricVehicles = document.getElementById("metricVehicles");
const metricCars = document.getElementById("metricCars");
const metricMotorcycles = document.getElementById("metricMotorcycles");
const metricSlots = document.getElementById("metricSlots");
const metricSearch = document.getElementById("metricSearch");
const metricDenied = document.getElementById("metricDenied");
const metricDeniedCars = document.getElementById("metricDeniedCars");
const metricDeniedMotorcycles = document.getElementById("metricDeniedMotorcycles");
const metricOccupancy = document.getElementById("metricOccupancy");
const metricCarSlotPeak = document.getElementById("metricCarSlotPeak");
const metricMotoSlotPeak = document.getElementById("metricMotoSlotPeak");
const metricExitComplete = document.getElementById("metricExitComplete");

let simulationData = null;
let frameIndex = 0;
let lastTick = 0;
let playing = true;
let slotNodes = new Map();
let carNodes = new Map();
let previousVehiclePoints = new Map();

function prettyMinutes(value) {
  return `${Number(value).toFixed(1)} min`;
}

function scenePoint(entity) {
  return {
    left: `${entity.x}%`,
    top: `${entity.y}%`,
  };
}

function renderSlotLayer(slots) {
  slotLayer.innerHTML = "";
  slotNodes = new Map();
  slots.forEach((slot) => {
    const node = document.createElement("div");
    node.className = slotClass(slot);
    node.title = `${slot.id} ${slot.slot_type}`;
    node.style.left = `${slot.x}%`;
    node.style.top = `${slot.y}%`;
    node.style.setProperty("--slot-angle", `${slot.angle || 0}deg`);
    node.style.zIndex = `${100 + slot.row}`;
    slotLayer.appendChild(node);
    slotNodes.set(slot.id, node);
  });
}

function slotClass(slot) {
  const typeClass = slot.slot_type === "motorcycle_slot" ? "slot-motorcycle" : "slot-car";
  return `topdown-slot ${typeClass} ${slot.state || "free"}`;
}

function vehicleVisualClass(car) {
  if (car.vehicle_type === "motorcycle") return "vehicle-motorcycle";
  if (car.id % 9 === 0) return "vehicle-van";
  if (car.id % 4 === 0) return "vehicle-suv";
  if (car.id % 7 === 0) return "vehicle-car vehicle-white";
  if (car.id % 6 === 0) return "vehicle-car vehicle-black";
  if (car.id % 5 === 0) return "vehicle-car vehicle-green";
  return car.id % 2 === 0 ? "vehicle-car vehicle-blue" : "vehicle-car";
}

function carClass(car) {
  const visibleStates = new Set(["entry_queue", "approaching_gate", "gate_wait", "gate_crossing", "searching", "parked", "exit_queue", "exiting", "denied"]);
  const stateClass = ["approaching_gate", "gate_crossing", "exit_queue"].includes(car.state) ? "searching" : car.state;
  const exitWaiting = car.state === "exiting" && car.exit_phase === "wait";
  const visibility = visibleStates.has(car.state) ? stateClass : "hidden-car";
  const motion = ["approaching_gate", "gate_crossing", "searching", "denied"].includes(car.state) || (car.state === "exiting" && !exitWaiting)
    ? "wheels-moving"
    : "wheels-stopped";
  const braking = ["gate_wait", "exit_queue", "parked"].includes(car.state) || exitWaiting ? "braking" : "";
  return `topdown-vehicle ${vehicleVisualClass(car)} ${visibility} ${motion} ${braking}`;
}

function createVehicleNode(car) {
  const node = document.createElement("div");
  node.className = carClass(car);
  node.innerHTML = `
    <span class="vehicle-shadow"></span>
    <span class="vehicle-body"></span>
    <span class="vehicle-wheel wheel-front"></span>
    <span class="vehicle-wheel wheel-back"></span>
    <span class="vehicle-headlight"></span>
    <span class="vehicle-brake-light"></span>
  `;
  node.style.transition = 'opacity 150ms ease';
  return node;
}

function movementAngle(car, point, node) {
  const previous = previousVehiclePoints.get(car.id);
  previousVehiclePoints.set(car.id, point);
  if (car.heading !== null && car.heading !== undefined) {
    return Number(car.heading);
  }
  if (!previous) return 90;

  const dx = parseFloat(point.left) - parseFloat(previous.left);
  const dy = parseFloat(point.top) - parseFloat(previous.top);
  if (Math.abs(dx) + Math.abs(dy) < 0.08) {
    return Number(node.dataset.angle || 90);
  }

  const raw = Math.atan2(dy, dx) * (180 / Math.PI) + 90;
  node.dataset.angle = String(raw);
  return raw;
}

function ensureCars(frame) {
  frame.cars.forEach((car) => {
    if (!carNodes.has(car.id)) {
      const node = createVehicleNode(car);
      carLayer.appendChild(node);
      carNodes.set(car.id, node);
    }
  });
}

function updateSlots(frame) {
  frame.slots.forEach((slot) => {
    const node = slotNodes.get(slot.id);
    if (!node) return;
    node.className = slotClass(slot);
  });
}

function interpolatePosition(x1, y1, x2, y2, t) {
  return {
    x: x1 + (x2 - x1) * t,
    y: y1 + (y2 - y1) * t,
  };
}

function shouldInterpolatePosition(car, nextCar) {
  if (!nextCar || car.state !== nextCar.state) return false;
  if (car.state !== "exiting") return true;

  // Respect the backend's lane-following exit path through the gate area.
  return car.exit_phase === "road" && nextCar.exit_phase === "road";
}

function renderFrame(frame, nextFrame, subProgress) {
  ensureCars(frame);
  updateSlots(frame);

  if (entryGateArm) {
    if (frame.entry_gate_open) {
      entryGateArm.classList.add("open");
    } else {
      entryGateArm.classList.remove("open");
    }
  }
  if (exitGateArm) {
    if (frame.exit_gate_open) {
      exitGateArm.classList.add("open");
    } else {
      exitGateArm.classList.remove("open");
    }
  }

  currentTime.textContent = prettyMinutes(frame.time_minutes);
  entryQueue.textContent = frame.current_entry_queue;
  availableSlots.textContent = frame.available_slots;
  exitQueue.textContent = frame.current_exit_queue;

  frame.cars.forEach((car) => {
    const node = carNodes.get(car.id);

    // Sub-frame interpolation between current and next frame
    let interpX = car.x;
    let interpY = car.y;
    const movingStates = new Set(["approaching_gate", "gate_crossing", "searching", "exiting", "denied"]);
    if (nextFrame && subProgress > 0 && movingStates.has(car.state)) {
      const nextCar = nextFrame.cars.find((c) => c.id === car.id);
      if (nextCar && movingStates.has(nextCar.state) && shouldInterpolatePosition(car, nextCar)) {
        const interp = interpolatePosition(car.x, car.y, nextCar.x, nextCar.y, subProgress);
        interpX = interp.x;
        interpY = interp.y;
      }
    }

    const point = { left: `${interpX}%`, top: `${interpY}%` };
    node.className = carClass(car);
    node.style.left = point.left;
    node.style.top = point.top;
    const angle = movementAngle(car, point, node);
    node.style.transform = `translate(-50%, -50%) rotate(${angle}deg)`;
    node.style.opacity = car.state === "scheduled" || car.state === "done" ? "0" : "1";
    node.style.zIndex = `${Math.round(interpY * 10)}`;
    node.title = `${car.vehicle_type} ${car.id}: ${car.exit_phase ? `${car.state}/${car.exit_phase}` : car.state}`;
  });
}

function updateSummary(metrics) {
  metricVehicles.textContent = metrics.total_vehicle_count;
  metricCars.textContent = metrics.total_cars;
  metricMotorcycles.textContent = metrics.total_motorcycles;
  metricSlots.textContent = metrics.total_slots;
  metricSearch.textContent = prettyMinutes(metrics.average_search_time_minutes);
  metricDenied.textContent = metrics.denied_vehicle_count;
  metricDeniedCars.textContent = metrics.denied_cars;
  metricDeniedMotorcycles.textContent = metrics.denied_motorcycles;
  metricOccupancy.textContent = `${metrics.occupancy_rate_percent}%`;
  metricCarSlotPeak.textContent = `${metrics.car_slot_occupancy_percent}%`;
  metricMotoSlotPeak.textContent = `${metrics.motorcycle_slot_occupancy_percent}%`;
  metricExitComplete.textContent = prettyMinutes(metrics.exit_completion_time_minutes);
}

function resetPlayback() {
  frameIndex = 0;
  lastTick = 0;
  if (simulationData) renderFrame(simulationData.frames[0], null, 0);
}

function tick(timestamp) {
  if (!playing || !simulationData) {
    window.requestAnimationFrame(tick);
    return;
  }

  if (!lastTick) lastTick = timestamp;
  const currentInterval = 400 / speedMultiplier;
  const elapsed = timestamp - lastTick;
  const subProgress = Math.min(1, elapsed / currentInterval);

  const nextFrameIndex = (frameIndex + 1) % simulationData.frames.length;
  const nextFrame = simulationData.frames[nextFrameIndex];
  renderFrame(simulationData.frames[frameIndex], nextFrame, subProgress);

  if (elapsed >= currentInterval) {
    frameIndex = nextFrameIndex;
    lastTick = timestamp;
  }
  window.requestAnimationFrame(tick);
}

async function loadSimulation(scenario) {
  const response = await fetch(`/api/simulation?scenario=${encodeURIComponent(scenario)}&t=${Date.now()}`);
  simulationData = await response.json();
  carLayer.innerHTML = "";
  carNodes = new Map();
  previousVehiclePoints = new Map();
  renderSlotLayer(simulationData.slots);
  updateSummary(simulationData.metrics);
  resetPlayback();
}

async function loadScenarios() {
  const response = await fetch("/api/scenarios");
  const payload = await response.json();
  Object.entries(payload.scenarios).forEach(([key, description]) => {
    const option = document.createElement("option");
    option.value = key;
    option.textContent = key.replaceAll("_", " ");
    option.title = description;
    scenarioSelect.appendChild(option);
  });
  await loadSimulation("baseline");
}

scenarioSelect.addEventListener("change", async (event) => {
  await loadSimulation(event.target.value);
});

playPauseButton.addEventListener("click", () => {
  playing = !playing;
  playPauseButton.textContent = playing ? "Pause" : "Play";
});

replayButton.addEventListener("click", () => {
  playing = true;
  playPauseButton.textContent = "Pause";
  resetPlayback();
});

if (speedSlider && speedValue) {
  speedSlider.addEventListener("input", (event) => {
    speedMultiplier = parseFloat(event.target.value);
    speedValue.textContent = `${speedMultiplier.toFixed(2)}x`;
    const duration = Math.round(400 / speedMultiplier);
    document.documentElement.style.setProperty("--transition-duration", `${duration}ms`);
  });
}

loadScenarios().then(() => {
  window.requestAnimationFrame(tick);
});
