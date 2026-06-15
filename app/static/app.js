const scenarioSelect = document.getElementById("scenarioSelect");
const playPauseButton = document.getElementById("playPauseButton");
const replayButton = document.getElementById("replayButton");
const slotLayer = document.getElementById("slotLayer");
const carLayer = document.getElementById("carLayer");
const entryGateArm = document.getElementById("entryGateArm");
const exitGateArm = document.getElementById("exitGateArm");
const speedSlider = document.getElementById("speedSlider");
const speedValue = document.getElementById("speedValue");
const simulationStatus = document.getElementById("simulationStatus");
const controlRail = document.querySelector(".control-rail");
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
const metricEntryWait = document.getElementById("metricEntryWait");
const metricExitWait = document.getElementById("metricExitWait");
const metricTimeInSystem = document.getElementById("metricTimeInSystem");
const metricEntryService = document.getElementById("metricEntryService");
const metricExitService = document.getElementById("metricExitService");
const metricThroughput = document.getElementById("metricThroughput");
const metricEntryUtil = document.getElementById("metricEntryUtil");
const metricExitUtil = document.getElementById("metricExitUtil");
const metricAvgEntryQueue = document.getElementById("metricAvgEntryQueue");
const metricAvgExitQueue = document.getElementById("metricAvgExitQueue");
const compareButton = document.getElementById("compareButton");
const comparePanel = document.getElementById("comparePanel");
const compareTableWrap = document.getElementById("compareTableWrap");
const compareCharts = document.getElementById("compareCharts");

let simulationData = null;
let compareData = null;
let frameIndex = 0;
let lastTick = 0;
let playing = true;
let slotNodes = new Map();
let carNodes = new Map();
let previousVehiclePoints = new Map();

function prettyMinutes(value) {
  return `${Number(value).toFixed(1)} min`;
}

function scenarioLabel(scenario) {
  return scenario.replaceAll("_", " ");
}

function setSimulationStatus(message, status = "idle") {
  if (!simulationStatus) return;
  simulationStatus.textContent = message;
  simulationStatus.dataset.status = status;
}

function setLoadingState(isLoading) {
  if (controlRail) {
    controlRail.classList.toggle("is-loading", isLoading);
  }
  scenarioSelect.disabled = isLoading;
  playPauseButton.disabled = isLoading || !simulationData;
  replayButton.disabled = isLoading || !simulationData;
  speedSlider.disabled = isLoading;
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`.trim());
  }
  return response.json();
}

const CUSTOM_MAP_COORDINATE_TRANSFORM = {
  xScale: 0.95815,
  xOffset: 1.94316,
  yScale: 1.03202,
  yOffset: 2.42282,
};

function clampPercent(value) {
  return Math.max(0, Math.min(100, value));
}

function usesCustomCoordinateGrid(x, y) {
  if (!document.body.classList.contains("custom-map")) return false;
  return x >= 24 && x <= 90 && y >= 12 && y <= 82;
}

function mapScenePoint(x, y) {
  if (!usesCustomCoordinateGrid(x, y)) {
    return { x, y };
  }
  const transform = CUSTOM_MAP_COORDINATE_TRANSFORM;
  const transformedX = clampPercent(x * transform.xScale + transform.xOffset);
  const transformedY = clampPercent(y * transform.yScale + transform.yOffset);
  return { x: transformedX, y: transformedY };
}

function scenePoint(entity) {
  const point = mapScenePoint(entity.x, entity.y);
  return {
    left: `${point.x}%`,
    top: `${point.y}%`,
  };
}

function renderSlotLayer(slots) {
  slotLayer.innerHTML = "";
  slotNodes = new Map();
  slots.forEach((slot) => {
    const node = document.createElement("div");
    node.className = slotClass(slot);
    node.title = `${slot.id} ${slot.slot_type}`;
    const slotPoint = mapScenePoint(slot.x, slot.y);
    node.style.left = `${slotPoint.x}%`;
    node.style.top = `${slotPoint.y}%`;
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
    node.style.zIndex = slot.state === "unavailable" ? "260" : `${100 + slot.row}`;
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
  return car.exit_phase === nextCar.exit_phase && ["merge", "road"].includes(car.exit_phase);
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
  // Custom-map animated gate arms (open with the same gate-state flags).
  customGateNodes.forEach((node) => {
    const open = node.dataset.gateType === "exit" ? frame.exit_gate_open : frame.entry_gate_open;
    node.classList.toggle("open", Boolean(open));
  });

  currentTime.textContent = prettyMinutes(frame.time_minutes);
  entryQueue.textContent = frame.current_entry_queue;
  availableSlots.textContent = frame.available_slots;
  exitQueue.textContent = frame.current_exit_queue;

  frame.cars.forEach((car) => {
    const node = carNodes.get(car.id);

    // Sub-frame interpolation between current and next frame
    let interpX = car.x;
    let interpY = car.y;
    const movingStates = new Set(["approaching_gate", "gate_crossing", "searching", "exit_queue", "exiting", "denied"]);
    if (nextFrame && subProgress > 0 && movingStates.has(car.state)) {
      const nextCar = nextFrame.cars.find((c) => c.id === car.id);
      if (nextCar && movingStates.has(nextCar.state) && shouldInterpolatePosition(car, nextCar)) {
        const interp = interpolatePosition(car.x, car.y, nextCar.x, nextCar.y, subProgress);
        interpX = interp.x;
        interpY = interp.y;
      }
    }

    const point = mapScenePoint(interpX, interpY);
    const cssPoint = { left: `${point.x}%`, top: `${point.y}%` };
    node.className = carClass(car);
    node.style.left = cssPoint.left;
    node.style.top = cssPoint.top;
    const angle = movementAngle(car, cssPoint, node);
    node.style.transform = `translate(-50%, -50%) rotate(${angle}deg)`;
    node.style.opacity = car.state === "scheduled" || car.state === "done" ? "0" : "1";
    node.style.zIndex = `${Math.round(point.y * 10)}`;
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
  metricEntryWait.textContent = prettyMinutes(metrics.average_entry_wait_minutes);
  metricExitWait.textContent = prettyMinutes(metrics.average_exit_wait_minutes);
  metricTimeInSystem.textContent = prettyMinutes(metrics.average_time_in_system_minutes);
  metricEntryService.textContent = prettyMinutes(metrics.average_entry_service_minutes);
  metricExitService.textContent = prettyMinutes(metrics.average_exit_service_minutes);
  metricThroughput.textContent = `${Number(metrics.throughput_vehicles_per_hour).toFixed(1)}/hr`;
  metricEntryUtil.textContent = `${metrics.entry_gate_utilization_percent}%`;
  metricExitUtil.textContent = `${metrics.exit_gate_utilization_percent}%`;
  metricAvgEntryQueue.textContent = Number(metrics.average_entry_queue_length).toFixed(1);
  metricAvgExitQueue.textContent = Number(metrics.average_exit_queue_length).toFixed(1);
}

// ---- Scenario comparison view ----
const COMPARE_COLUMNS = [
  { key: "average_entry_wait_minutes", label: "Entry wait", unit: "min", better: "low" },
  { key: "average_exit_wait_minutes", label: "Exit wait", unit: "min", better: "low" },
  { key: "average_time_in_system_minutes", label: "Time in system", unit: "min", better: "low" },
  { key: "throughput_vehicles_per_hour", label: "Throughput", unit: "/hr", better: "high" },
  { key: "entry_gate_utilization_percent", label: "Entry gate util", unit: "%", better: "high" },
  { key: "exit_gate_utilization_percent", label: "Exit gate util", unit: "%", better: "high" },
  { key: "max_entry_queue_length", label: "Max entry queue", unit: "", better: "low" },
  { key: "max_exit_queue_length", label: "Max exit queue", unit: "", better: "low" },
  { key: "denied_vehicle_count", label: "Denied", unit: "", better: "low" },
];

const COMPARE_CHARTS = [
  { key: "average_entry_wait_minutes", label: "Average entry wait (min)" },
  { key: "average_exit_wait_minutes", label: "Average exit wait (min)" },
  { key: "throughput_vehicles_per_hour", label: "Throughput (vehicles/hr)" },
  { key: "entry_gate_utilization_percent", label: "Entry gate utilization (%)" },
  { key: "exit_gate_utilization_percent", label: "Exit gate utilization (%)" },
];

function renderCompare(payload) {
  const names = Object.keys(payload.scenarios);
  // Table
  const header =
    `<tr><th>Metric</th>${names.map((n) => `<th>${scenarioLabel(n)}</th>`).join("")}</tr>`;
  const rows = COMPARE_COLUMNS.map((col) => {
    const vals = names.map((n) => payload.scenarios[n].metrics[col.key]);
    const best = col.better === "low" ? Math.min(...vals) : Math.max(...vals);
    const cells = names
      .map((n, i) => {
        const v = vals[i];
        const isBest = v === best;
        const shown = col.unit === "/hr" || col.unit === "min" ? Number(v).toFixed(1) : v;
        return `<td class="${isBest ? "best" : ""}">${shown}${col.unit}</td>`;
      })
      .join("");
    return `<tr><th>${col.label}</th>${cells}</tr>`;
  }).join("");
  compareTableWrap.innerHTML = `<table class="compare-table">${header}${rows}</table>`;

  // Bar charts (dependency-free)
  compareCharts.innerHTML = COMPARE_CHARTS.map((chart) => {
    const entries = names.map((n) => ({ n, v: Number(payload.scenarios[n].metrics[chart.key]) }));
    const max = Math.max(...entries.map((e) => e.v), 1);
    const bars = entries
      .map(
        (e) =>
          `<div class="bar-row"><span class="bar-label">${scenarioLabel(e.n)}</span>` +
          `<span class="bar-track"><span class="bar-fill" style="width:${(e.v / max) * 100}%"></span></span>` +
          `<span class="bar-value">${e.v.toFixed(1)}</span></div>`
      )
      .join("");
    return `<div class="chart"><h3>${chart.label}</h3>${bars}</div>`;
  }).join("");
}

async function ensureCompareData() {
  if (compareData) return compareData;
  compareData = await fetchJson(`/api/compare?t=${Date.now()}`);
  return compareData;
}

async function toggleCompare() {
  const showing = !comparePanel.hidden;
  if (showing) {
    comparePanel.hidden = true;
    compareButton.textContent = "Compare scenarios";
    return;
  }
  compareButton.textContent = "Loading...";
  try {
    const payload = await ensureCompareData();
    renderCompare(payload);
    comparePanel.hidden = false;
    comparePanel.scrollIntoView({ behavior: "smooth", block: "start" });
    compareButton.textContent = "Hide comparison";
  } catch (error) {
    console.error("Failed to load comparison", error);
    compareButton.textContent = "Compare scenarios";
  }
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
  // Base frame interval. 1x now plays at what used to be 10x; the slider goes up from there.
  const currentInterval = 40 / speedMultiplier;
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

const DEFAULT_BACKGROUND = "/static/assets/generated/custom-parking-background.png";
const SCENARIO_BACKGROUNDS = {
  two_entrance_two_exit: "/static/assets/generated/map-two-entrance-two-exit.png?v=3",
  two_entrance_one_exit: "/static/assets/generated/map-two-entrance-one-exit.png?v=3",
  one_entrance_two_exit: "/static/assets/generated/map-one-entrance-two-exit.png?v=3",
};

function applyScenarioBackground(scenario) {
  const custom = SCENARIO_BACKGROUNDS[scenario];
  const url = custom || DEFAULT_BACKGROUND;
  document.documentElement.style.setProperty("--map-background", `url("${url}")`);
  // Custom maps draw their own labels, so hide the base-map overlay markers; the
  // animated gate arms are rebuilt per-map below.
  document.body.classList.toggle("custom-map", Boolean(custom));
  buildCustomGates(scenario);
}

// Animated gate arms per gate-layout map. Positions are % of the map surface
// (top/left); arms rotate open via the .map-gate.open class, driven by the same
// entry/exit gate-state flags as the default map.
const SCENARIO_GATES = {
  two_entrance_two_exit: [
    { type: "entry", top: 23.6, left: 6.6, width: 7.6 },
    { type: "entry", top: 64.2, left: 6.6, width: 7.6 },
    { type: "exit", top: 34.2, left: 92.2, width: 8.8 },
    { type: "exit", top: 69.3, left: 92.2, width: 8.8 },
  ],
  two_entrance_one_exit: [
    { type: "entry", top: 23.6, left: 6.6, width: 7.6 },
    { type: "entry", top: 64.2, left: 6.6, width: 7.6 },
    { type: "exit", top: 38.8, left: 92.2, width: 8.8 },
  ],
  one_entrance_two_exit: [
    { type: "entry", top: 24.7, left: 4.8, width: 7.4 },
    { type: "exit", top: 34.2, left: 92.2, width: 8.8 },
    { type: "exit", top: 69.3, left: 92.2, width: 8.8 },
  ],
};

let customGateNodes = [];

function buildCustomGates(scenario) {
  const map = document.getElementById("parkingMap");
  customGateNodes.forEach((n) => n.remove());
  customGateNodes = [];
  const gates = SCENARIO_GATES[scenario];
  if (!map || !gates) return;
  gates.forEach((g) => {
    const arm = document.createElement("div");
    arm.className = `map-gate map-gate-${g.type}`;
    arm.dataset.gateType = g.type;
    arm.style.top = `${g.top}%`;
    arm.style.left = `${g.left}%`;
    arm.style.width = `${g.width || 6}%`;
    map.appendChild(arm);
    customGateNodes.push(arm);
  });
}

function customParamQuery() {
  const fields = [
    ["total_cars", "inputCars"],
    ["slot_count", "inputSlots"],
    ["entry_gates", "inputEntryGates"],
    ["exit_gates", "inputExitGates"],
    ["entry_service", "inputEntryService"],
    ["exit_service", "inputExitService"],
  ];
  let query = "";
  for (const [param, id] of fields) {
    const el = document.getElementById(id);
    if (el && el.value !== "" && el.value !== null) {
      query += `&${param}=${encodeURIComponent(el.value)}`;
    }
  }
  return query;
}

async function loadSimulation(scenario) {
  setLoadingState(true);
  setSimulationStatus(`Loading ${scenarioLabel(scenario)}...`, "loading");
  applyScenarioBackground(scenario);
  try {
    const nextSimulationData = await fetchJson(
      `/api/simulation?scenario=${encodeURIComponent(scenario)}${customParamQuery()}&t=${Date.now()}`
    );
    simulationData = nextSimulationData;
    carLayer.innerHTML = "";
    carNodes = new Map();
    previousVehiclePoints = new Map();
    renderSlotLayer(simulationData.slots);
    updateSummary(simulationData.metrics);
    resetPlayback();
    setSimulationStatus(`${scenarioLabel(scenario)} ready`, "ready");
  } catch (error) {
    console.error("Failed to load simulation", error);
    setSimulationStatus("Could not load simulation. Keeping the last valid run.", "error");
  } finally {
    setLoadingState(false);
  }
}

async function loadScenarios() {
  setLoadingState(true);
  setSimulationStatus("Loading scenarios...", "loading");
  try {
    const payload = await fetchJson("/api/scenarios");
    scenarioSelect.innerHTML = "";
    Object.entries(payload.scenarios).forEach(([key, description]) => {
      const option = document.createElement("option");
      option.value = key;
      option.textContent = scenarioLabel(key);
      option.title = description;
      scenarioSelect.appendChild(option);
    });
    await loadSimulation("baseline");
  } catch (error) {
    console.error("Failed to load scenarios", error);
    setSimulationStatus("Could not load scenarios. Check the local server and retry.", "error");
  } finally {
    setLoadingState(false);
  }
}

scenarioSelect.addEventListener("change", async (event) => {
  await loadSimulation(event.target.value);
});

playPauseButton.addEventListener("click", () => {
  if (!simulationData) return;
  playing = !playing;
  playPauseButton.textContent = playing ? "Pause" : "Play";
});

replayButton.addEventListener("click", () => {
  if (!simulationData) return;
  playing = true;
  playPauseButton.textContent = "Pause";
  resetPlayback();
});

if (compareButton) {
  compareButton.addEventListener("click", toggleCompare);
}

const applyParamsButton = document.getElementById("applyParamsButton");
const resetParamsButton = document.getElementById("resetParamsButton");
if (applyParamsButton) {
  applyParamsButton.addEventListener("click", async () => {
    await loadSimulation(scenarioSelect.value);
  });
}
if (resetParamsButton) {
  resetParamsButton.addEventListener("click", async () => {
    ["inputCars", "inputSlots", "inputEntryGates", "inputExitGates", "inputEntryService", "inputExitService"]
      .forEach((id) => { const el = document.getElementById(id); if (el) el.value = ""; });
    await loadSimulation(scenarioSelect.value);
  });
}

if (speedSlider && speedValue) {
  speedSlider.addEventListener("input", (event) => {
    speedMultiplier = parseFloat(event.target.value);
    speedValue.textContent = `${speedMultiplier.toFixed(2)}x`;
    const duration = Math.round(40 / speedMultiplier);
    document.documentElement.style.setProperty("--transition-duration", `${duration}ms`);
  });
}

setLoadingState(true);
loadScenarios().then(() => {
  window.requestAnimationFrame(tick);
});
