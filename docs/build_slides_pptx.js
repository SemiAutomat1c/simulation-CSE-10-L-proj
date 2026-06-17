"use strict";
// NODE_PATH=$(npm root -g) node docs/build_slides_pptx.js
const pptxgen = require("pptxgenjs");
const path = require("path");

// ── palette (light theme throughout) ──────────────────────────────────────
const NAVY   = "1F4E79";   // primary headings
const BLUE   = "2E75B6";   // secondary / subheadings
const ORANGE = "C55A11";   // accent callouts
const BGWHITE = "FFFFFF";
const BGLIGHT = "F0F4FA";  // alternate card bg
const RULE    = "BDD0E9";  // horizontal rule colour
const BODY    = "2D3748";  // body text
const MUTED   = "64748B";  // captions / notes
const GRAY1   = "EDF2F8";  // table zebra
const GRAY2   = "D5E3F0";  // table header tint

const W = 10, H = 5.625;   // 16×9 slide inches

const pres = new pptxgen();
pres.layout  = "LAYOUT_16x9";
pres.author  = "CSE 10/L Group";
pres.title   = "Mall Parking Flow – Modeling & Simulation";

// ── shared helpers ─────────────────────────────────────────────────────────
function slide(bg) {
  const s = pres.addSlide();
  s.background = { color: bg || BGWHITE };
  return s;
}

// standard header: section label (small caps colour) + large title
function header(s, label, title, titleSize) {
  s.addText(label.toUpperCase(), {
    x: 0.45, y: 0.22, w: 9.1, h: 0.25,
    fontSize: 9, bold: true, color: ORANGE, charSpacing: 2, margin: 0,
  });
  s.addText(title, {
    x: 0.45, y: 0.45, w: 9.1, h: 0.75,
    fontSize: titleSize || 28, bold: true, color: NAVY, margin: 0,
  });
  // thin rule under title
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.45, y: 1.22, w: 9.1, h: 0.025, fill: { color: RULE }, line: { color: RULE, width: 0 },
  });
}

// small callout box
function callout(s, x, y, w, h, label, value, valueSz, labelColor) {
  s.addShape(pres.shapes.RECTANGLE, {
    x, y, w, h, fill: { color: BGLIGHT }, line: { color: RULE, width: 1 },
  });
  s.addText(value, {
    x: x + 0.08, y: y + 0.08, w: w - 0.16, h: h * 0.55,
    fontSize: valueSz || 22, bold: true, color: labelColor || NAVY,
    align: "center", valign: "middle", margin: 0,
  });
  s.addText(label, {
    x: x + 0.08, y: y + h * 0.58, w: w - 0.16, h: h * 0.36,
    fontSize: 8.5, color: MUTED, align: "center", margin: 0,
  });
}

// bullet list helper
function bullets(s, items, x, y, w, h, sz) {
  const runs = items.map((txt, i) => ({
    text: txt,
    options: { bullet: true, breakLine: i < items.length - 1 },
  }));
  s.addText(runs, {
    x, y, w, h,
    fontSize: sz || 13.5, color: BODY, valign: "top",
    paraSpaceAfter: 4, lineSpacingMultiple: 1.15,
  });
}

// native bar chart (horizontal)
function hBar(s, labels, values, colors, x, y, w, h, title) {
  s.addChart(pres.charts.BAR, [{
    name: title || "",
    labels,
    values,
  }], {
    x, y, w, h,
    barDir: "bar",
    chartColors: colors,
    chartArea: { fill: { color: BGWHITE }, roundedCorners: false },
    catAxisLabelColor: BODY,
    valAxisLabelColor: MUTED,
    valGridLine: { color: "E2E8F0", size: 0.5 },
    catGridLine: { style: "none" },
    showValue: true,
    dataLabelColor: BODY,
    dataLabelFontSize: 10,
    showLegend: false,
    showTitle: false,
    valAxisMinVal: 0,
  });
}

// ──────────────────────────────────────────────────────────────────────────
// SLIDE 1 – Title
// ──────────────────────────────────────────────────────────────────────────
{
  const s = slide(BGWHITE);
  // left accent bar
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.12, h: H, fill: { color: NAVY }, line: { color: NAVY, width: 0 },
  });
  // blue tint block behind title area
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.12, y: 1.1, w: W - 0.12, h: 2.6,
    fill: { color: BGLIGHT }, line: { color: BGLIGHT, width: 0 },
  });
  s.addText("MALL PARKING FLOW", {
    x: 0.5, y: 1.2, w: 9.1, h: 0.9,
    fontSize: 40, bold: true, color: NAVY, margin: 0,
  });
  s.addText("A Discrete-Event Simulation of Entry, Parking & Exit Congestion", {
    x: 0.5, y: 2.12, w: 8.5, h: 0.55,
    fontSize: 16, color: BLUE, italic: true, margin: 0,
  });
  s.addText("CSE 10/L – Modeling and Simulation", {
    x: 0.5, y: 2.72, w: 7, h: 0.35,
    fontSize: 12.5, color: MUTED, margin: 0,
  });
  // fill-in fields — two rows so nothing clips the right edge
  const fieldY = 3.7, fh = 0.3;
  // row 1: Group Members + Instructor
  [["Group Members:", 4.5], ["Instructor:", 4.0]].forEach(([lbl, w], i) => {
    const fx = 0.5 + i * 5.0;
    s.addText(lbl, { x: fx, y: fieldY, w: w, h: fh, fontSize: 10.5, bold: true, color: NAVY, margin: 0 });
    s.addShape(pres.shapes.LINE, { x: fx, y: fieldY + fh, w: w - 0.1, h: 0, line: { color: RULE, width: 1.2 } });
  });
  // row 2: Section + Date
  [["Section:", 2.8], ["Date:", 2.8]].forEach(([lbl, w], i) => {
    const fx = 0.5 + i * 3.2;
    s.addText(lbl, { x: fx, y: fieldY + 0.55, w: w, h: fh, fontSize: 10.5, bold: true, color: NAVY, margin: 0 });
    s.addShape(pres.shapes.LINE, { x: fx, y: fieldY + 0.55 + fh, w: w - 0.1, h: 0, line: { color: RULE, width: 1.2 } });
  });
  // bottom note
  s.addText("Department of Arts and Sciences Education · Computer Science Program · UM Visayan Campus, Tagum City", {
    x: 0.5, y: 5.22, w: 9.0, h: 0.28,
    fontSize: 7.5, color: MUTED, align: "center", margin: 0,
  });
}

// ──────────────────────────────────────────────────────────────────────────
// SLIDE 2 – Introduction
// ──────────────────────────────────────────────────────────────────────────
{
  const s = slide();
  header(s, "Item 1", "Introduction");
  // two columns
  const col1x = 0.45, col2x = 5.3, colW = 4.5, top = 1.45;
  s.addText("A parking lot is a queuing system", {
    x: col1x, y: top, w: colW, h: 0.4,
    fontSize: 14.5, bold: true, color: NAVY, margin: 0,
  });
  bullets(s, [
    "Vehicles arrive → wait at entry gate → search & park → shop → queue at exit gate → leave.",
    "Each gate lane serves one vehicle at a time; the lot has finite slots.",
    "Congestion (queues) forms whenever demand outpaces service.",
  ], col1x, top + 0.42, colW, 1.5, 12.5);

  s.addText("Built with Python + SimPy", {
    x: col1x, y: top + 2.05, w: colW, h: 0.35,
    fontSize: 14.5, bold: true, color: NAVY, margin: 0,
  });
  bullets(s, [
    "Discrete-event simulation (DES) models the lot event by event.",
    "Top-down browser dashboard visualizes queues, gates, and slots live.",
    "Two independent axes: Scenario (demand) × Map (gate layout).",
  ], col1x, top + 2.42, colW, 1.5, 12.5);

  // right column – visual summary
  s.addShape(pres.shapes.RECTANGLE, {
    x: col2x, y: top, w: colW, h: 3.85,
    fill: { color: BGLIGHT }, line: { color: RULE, width: 1 },
  });
  s.addText("Vehicle Journey", {
    x: col2x + 0.15, y: top + 0.12, w: colW - 0.3, h: 0.32,
    fontSize: 12, bold: true, color: NAVY, align: "center", margin: 0,
  });
  const steps = ["Arrive", "Entry Queue", "Entry Gate", "Search & Park", "Dwell (shop)", "Exit Queue", "Exit Gate", "Done"];
  const arrowColor = BLUE;
  steps.forEach((step, i) => {
    const sy = top + 0.52 + i * 0.41;
    const isQueue = step.includes("Queue");
    const isGate  = step.includes("Gate");
    const fillC   = isQueue ? GRAY2 : isGate ? "D6E4F0" : BGWHITE;
    s.addShape(pres.shapes.RECTANGLE, {
      x: col2x + 0.4, y: sy, w: colW - 0.8, h: 0.28,
      fill: { color: fillC }, line: { color: RULE, width: 0.7 },
    });
    s.addText(step, {
      x: col2x + 0.4, y: sy, w: colW - 0.8, h: 0.28,
      fontSize: 10, color: BODY, align: "center", valign: "middle", margin: 0,
    });
    if (i < steps.length - 1) {
      s.addShape(pres.shapes.LINE, {
        x: col2x + colW / 2 - 0.01, y: sy + 0.28, w: 0, h: 0.13,
        line: { color: arrowColor, width: 1 },
      });
    }
  });
}

// ──────────────────────────────────────────────────────────────────────────
// SLIDE 3 – Problem Definition
// ──────────────────────────────────────────────────────────────────────────
{
  const s = slide();
  header(s, "Item 2", "Problem Definition");
  const top = 1.45;
  const cards = [
    { title: "Entry Gate Bottleneck", body: "A queue builds when arrivals cluster or the gate is slow. Vehicles wait before they can even enter the lot.", color: BLUE },
    { title: "Exit Gate Bottleneck",  body: "A queue builds when many vehicles leave at once or exit processing is slow. Can trap parked cars for long periods.", color: NAVY },
    { title: "Denials (Lot Full)",    body: "When the lot is full, vehicles are denied entry entirely — lost visits for the mall.", color: ORANGE },
  ];
  cards.forEach((c, i) => {
    const x = 0.45 + i * 3.15;
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: top, w: 3.0, h: 2.2,
      fill: { color: BGLIGHT }, line: { color: c.color, width: 2 },
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: top, w: 3.0, h: 0.38,
      fill: { color: c.color }, line: { color: c.color, width: 0 },
    });
    s.addText(c.title, {
      x: x + 0.12, y: top + 0.02, w: 2.76, h: 0.34,
      fontSize: 11.5, bold: true, color: BGWHITE, valign: "middle", margin: 0,
    });
    s.addText(c.body, {
      x: x + 0.12, y: top + 0.48, w: 2.76, h: 1.6,
      fontSize: 11.5, color: BODY, valign: "top", lineSpacingMultiple: 1.2, margin: 0,
    });
  });

  // "Why it matters"
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.45, y: top + 2.38, w: 9.1, h: 0.9,
    fill: { color: GRAY1 }, line: { color: RULE, width: 1 },
  });
  s.addText("Why it matters:", {
    x: 0.62, y: top + 2.48, w: 1.5, h: 0.32, fontSize: 11.5, bold: true, color: NAVY, margin: 0,
  });
  s.addText(
    "Long waits hurt customer experience and can spill onto public roads. Denials = lost visits. " +
    "Management needs to know which bottleneck dominates — and whether a second gate lane is worth it.",
    { x: 2.1, y: top + 2.45, w: 7.3, h: 0.65, fontSize: 11, color: BODY, lineSpacingMultiple: 1.2, margin: 0 }
  );
}

// ──────────────────────────────────────────────────────────────────────────
// SLIDE 4 – Objectives
// ──────────────────────────────────────────────────────────────────────────
{
  const s = slide();
  header(s, "Item 3", "Objectives");
  const top = 1.42;
  const items = [
    { num: "1", txt: "Analyze queue performance at the entry and exit gates (waiting time and queue length)." },
    { num: "2", txt: "Measure resource utilization of the entry gate(s), exit gate(s), and parking capacity." },
    { num: "3", txt: "Quantify throughput (vehicles completed per hour) and total time-in-system." },
    { num: "4", txt: "Compare operational scenarios — different arrival patterns, reduced capacity, slow entry, slow exit — to identify the dominant bottleneck." },
    { num: "5", txt: "Compare gate configurations — same demand on 1-gate vs. 2-gate maps (\"one cashier vs. two cashiers\").", highlight: true },
  ];
  items.forEach((item, i) => {
    const y = top + i * 0.76;
    const bg = item.highlight ? "FFF3E0" : (i % 2 === 0 ? BGLIGHT : BGWHITE);
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.45, y, w: 9.1, h: 0.66,
      fill: { color: bg }, line: { color: RULE, width: 0.8 },
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.45, y, w: 0.52, h: 0.66,
      fill: { color: item.highlight ? ORANGE : NAVY }, line: { color: NAVY, width: 0 },
    });
    s.addText(item.num, {
      x: 0.45, y, w: 0.52, h: 0.66,
      fontSize: 16, bold: true, color: BGWHITE, align: "center", valign: "middle", margin: 0,
    });
    s.addText(item.txt, {
      x: 1.08, y: y + 0.06, w: 8.3, h: 0.54,
      fontSize: 12, color: BODY, valign: "middle", lineSpacingMultiple: 1.1, margin: 0,
    });
  });
}

// ──────────────────────────────────────────────────────────────────────────
// SLIDE 5 – System Model: DES Elements
// ──────────────────────────────────────────────────────────────────────────
{
  const s = slide();
  header(s, "Item 4a", "System Model & Design — DES Elements");
  const top = 1.42;
  const rows = [
    ["Entities",        "Vehicles (cars & motorcycles) — each with arrival time, type, and assigned lane."],
    ["Events",          "Arrival · gate service start/end · gate crossing · search/park · exit request · departure."],
    ["Resources",       "Entry gate(s) and exit gate(s) (SimPy Resource, capacity 1 per lane) + typed parking slot pools."],
    ["Queues",          "Entry queue(s) and exit queue(s), FIFO. Each gate lane has its own queue."],
    ["State variables", "Per-vehicle state ×11 · queue lengths · slots free/occupied · denied/completed count · sim clock."],
  ];
  rows.forEach(([label, desc], i) => {
    const y = top + i * 0.75;
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.45, y, w: 9.1, h: 0.65,
      fill: { color: i % 2 === 0 ? BGLIGHT : BGWHITE }, line: { color: RULE, width: 0.8 },
    });
    s.addText(label, {
      x: 0.58, y: y + 0.06, w: 1.7, h: 0.52,
      fontSize: 11.5, bold: true, color: NAVY, valign: "middle", margin: 0,
    });
    s.addShape(pres.shapes.LINE, {
      x: 2.28, y: y + 0.1, w: 0, h: 0.45, line: { color: RULE, width: 1 },
    });
    s.addText(desc, {
      x: 2.42, y: y + 0.06, w: 6.95, h: 0.52,
      fontSize: 11.5, color: BODY, valign: "middle", lineSpacingMultiple: 1.1, margin: 0,
    });
  });
  // note at bottom
  s.addText("Simulation type: discrete-event · single replication per (scenario × map) · deterministic seeded RNG", {
    x: 0.45, y: top + 3.82, w: 9.1, h: 0.28,
    fontSize: 9.5, italic: true, color: MUTED, margin: 0,
  });
}

// ──────────────────────────────────────────────────────────────────────────
// SLIDE 6 – System Model: Two Axes
// ──────────────────────────────────────────────────────────────────────────
{
  const s = slide();
  header(s, "Item 4a", "Two Independent Configuration Axes");
  const top = 1.42;

  // Scenario axis
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.45, y: top, w: 4.4, h: 3.7,
    fill: { color: BGLIGHT }, line: { color: BLUE, width: 1.5 },
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.45, y: top, w: 4.4, h: 0.38,
    fill: { color: BLUE }, line: { color: BLUE, width: 0 },
  });
  s.addText("SCENARIO  (Demand Profile)", {
    x: 0.55, y: top + 0.02, w: 4.2, h: 0.34,
    fontSize: 11, bold: true, color: BGWHITE, valign: "middle", margin: 0,
  });
  bullets(s, [
    "How busy the lot is + how fast gates serve.",
    "Sets: # vehicles, arrival pattern, usable slots, entry/exit service times.",
    "5 profiles: baseline, rush_hour, limited_slots, slow_entry, exit_congestion",
  ], 0.58, top + 0.48, 4.1, 1.2, 11.5);
  // scenario chips
  const scNames = ["baseline", "rush_hour", "limited_slots", "slow_entry", "exit_congestion"];
  scNames.forEach((n, i) => {
    const cx = 0.62 + (i % 2) * 2.1;
    const cy = top + 1.8 + Math.floor(i / 2) * 0.42;
    s.addShape(pres.shapes.RECTANGLE, {
      x: cx, y: cy, w: 1.95, h: 0.3,
      fill: { color: GRAY2 }, line: { color: BLUE, width: 0.7 },
    });
    s.addText(n, {
      x: cx, y: cy, w: 1.95, h: 0.3,
      fontSize: 9.5, color: NAVY, align: "center", valign: "middle", margin: 0,
    });
  });

  // Map axis
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.15, y: top, w: 4.4, h: 3.7,
    fill: { color: BGLIGHT }, line: { color: NAVY, width: 1.5 },
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.15, y: top, w: 4.4, h: 0.38,
    fill: { color: NAVY }, line: { color: NAVY, width: 0 },
  });
  s.addText("MAP  (Gate Layout)", {
    x: 5.25, y: top + 0.02, w: 4.2, h: 0.34,
    fontSize: 11, bold: true, color: BGWHITE, valign: "middle", margin: 0,
  });
  bullets(s, [
    "How many entry / exit gate lanes exist (1 or 2 each).",
    "Sets SimPy resource capacity; 2-gate map = 2 parallel single-server lanes.",
  ], 5.28, top + 0.48, 4.1, 0.9, 11.5);
  const mapRows = [
    ["one_entrance_one_exit",   "1 entry  ·  1 exit"],
    ["two_entrance_one_exit",   "2 entry  ·  1 exit"],
    ["one_entrance_two_exit",   "1 entry  ·  2 exit"],
    ["two_entrance_two_exit",   "2 entry  ·  2 exit"],
  ];
  mapRows.forEach(([name, desc], i) => {
    const my = top + 1.52 + i * 0.5;
    s.addShape(pres.shapes.RECTANGLE, {
      x: 5.28, y: my, w: 4.12, h: 0.4,
      fill: { color: i % 2 === 0 ? GRAY2 : BGWHITE }, line: { color: RULE, width: 0.7 },
    });
    s.addText(name, {
      x: 5.35, y: my + 0.02, w: 2.0, h: 0.36,
      fontSize: 9.5, bold: true, color: NAVY, valign: "middle", margin: 0,
    });
    s.addText(desc, {
      x: 7.36, y: my + 0.02, w: 1.9, h: 0.36,
      fontSize: 9.5, color: MUTED, valign: "middle", align: "right", margin: 0,
    });
  });

  // arrow in between
  s.addText("×", {
    x: 4.74, y: top + 1.55, w: 0.42, h: 0.42,
    fontSize: 28, bold: true, color: ORANGE, align: "center", valign: "middle", margin: 0,
  });
  s.addText("any\ncombination", {
    x: 4.68, y: top + 3.1, w: 0.54, h: 0.45,
    fontSize: 7.5, color: MUTED, align: "center", italic: true, margin: 0,
  });
}

// ──────────────────────────────────────────────────────────────────────────
// SLIDE 7 – Process Flow
// ──────────────────────────────────────────────────────────────────────────
{
  const s = slide();
  header(s, "Item 4b", "Vehicle Lifecycle — Process Flow");
  const top = 1.45;

  // render the 11 states as a horizontal pipeline with denied branch
  const states = [
    { lbl: "scheduled",       col: BGWHITE,  border: RULE  },
    { lbl: "entry_queue",     col: GRAY2,    border: BLUE  },
    { lbl: "approaching\ngate", col: BGWHITE, border: RULE },
    { lbl: "gate_wait",       col: "D6E4F0", border: NAVY  },
    { lbl: "gate_crossing",   col: BGWHITE,  border: RULE  },
    { lbl: "searching",       col: BGWHITE,  border: RULE  },
    { lbl: "parked",          col: GRAY2,    border: BLUE  },
    { lbl: "exit_queue",      col: GRAY2,    border: BLUE  },
    { lbl: "exiting",         col: "D6E4F0", border: NAVY  },
    { lbl: "done",            col: "D6EDD8", border: "2E7D32" },
  ];
  const boxW = 0.80, boxH = 0.56, startX = 0.3, rowY = top;
  const arrowW = 0.09;
  states.forEach((st, i) => {
    const x = startX + i * (boxW + arrowW);
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: rowY, w: boxW, h: boxH,
      fill: { color: st.col }, line: { color: st.border, width: 1.2 },
    });
    s.addText(st.lbl, {
      x, y: rowY, w: boxW, h: boxH,
      fontSize: 7.8, color: NAVY, align: "center", valign: "middle", margin: 0,
    });
    if (i < states.length - 1) {
      s.addShape(pres.shapes.LINE, {
        x: x + boxW, y: rowY + boxH / 2, w: arrowW, h: 0,
        line: { color: NAVY, width: 1 },
      });
    }
  });

  // denied branch (from gate_wait area, index 3/4 boundary, going down)
  const deniedX = startX + 3 * (boxW + arrowW) + boxW - 0.2;
  const deniedY = rowY + boxH + 0.15;
  s.addShape(pres.shapes.RECTANGLE, {
    x: deniedX, y: deniedY, w: 1.0, h: 0.46,
    fill: { color: "FFF3E0" }, line: { color: ORANGE, width: 1.5, dashType: "dash" },
  });
  s.addText("DENIED", {
    x: deniedX, y: deniedY, w: 1.0, h: 0.46,
    fontSize: 10, bold: true, color: ORANGE, align: "center", valign: "middle", margin: 0,
  });
  s.addText("(no compatible slot)", {
    x: deniedX - 0.15, y: deniedY + 0.48, w: 1.3, h: 0.22,
    fontSize: 7.5, color: MUTED, align: "center", margin: 0,
  });
  // arrow from denied → exit_queue (index 7)
  const exitQueueX = startX + 7 * (boxW + arrowW);
  s.addShape(pres.shapes.LINE, {
    x: deniedX + 0.5, y: deniedY + 0.46, w: 0, h: 0.25,
    line: { color: ORANGE, width: 0.8 },
  });
  s.addShape(pres.shapes.LINE, {
    x: deniedX + 0.5, y: deniedY + 0.71, w: exitQueueX - deniedX - 0.1, h: 0,
    line: { color: ORANGE, width: 0.8 },
  });
  s.addShape(pres.shapes.LINE, {
    x: exitQueueX + 0.4, y: rowY + boxH, w: 0, h: deniedY + 0.71 - rowY - boxH,
    line: { color: ORANGE, width: 0.8 },
  });

  // state mapping text
  s.addText("Resources held:", {
    x: 0.2, y: top + 1.55, w: 1.4, h: 0.28, fontSize: 10.5, bold: true, color: NAVY, margin: 0,
  });
  s.addText(
    "Entry gate: approach → cross.   Exit gate: exit service → merge.   Parking slot: reserved at gate → released on exit request.",
    { x: 1.65, y: top + 1.55, w: 8.1, h: 0.28, fontSize: 10.5, color: BODY, margin: 0 }
  );

  // Legend
  const leg = [
    { col: GRAY2, border: BLUE,    lbl: "Queue" },
    { col: "D6E4F0", border: NAVY, lbl: "Gate service" },
    { col: "D6EDD8", border: "2E7D32", lbl: "Terminal" },
    { col: "FFF3E0", border: ORANGE,   lbl: "Denied branch" },
  ];
  leg.forEach((l, i) => {
    const lx = 0.2 + i * 2.35;
    s.addShape(pres.shapes.RECTANGLE, {
      x: lx, y: top + 2.05, w: 0.35, h: 0.22,
      fill: { color: l.col }, line: { color: l.border, width: 1 },
    });
    s.addText(l.lbl, {
      x: lx + 0.42, y: top + 2.05, w: 1.85, h: 0.22,
      fontSize: 9, color: BODY, valign: "middle", margin: 0,
    });
  });

  // full mapping
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.2, y: top + 2.42, w: 9.6, h: 0.68,
    fill: { color: BGLIGHT }, line: { color: RULE, width: 0.8 },
  });
  s.addText("State mapping:  ", {
    x: 0.35, y: top + 2.54, w: 1.3, h: 0.44,
    fontSize: 9.5, bold: true, color: NAVY, margin: 0,
  });
  s.addText(
    "scheduled (A) → entry_queue (B) → approaching_gate (D) → gate_wait (E) → gate_crossing (H) → " +
    "searching (I) → parked (J) → exit_queue (L) → exiting (N/O) → done (P)   +   denied branch from G",
    { x: 1.6, y: top + 2.5, w: 7.95, h: 0.55, fontSize: 9.5, color: BODY, lineSpacingMultiple: 1.15, margin: 0 }
  );
}

// ──────────────────────────────────────────────────────────────────────────
// SLIDE 8 – Assumptions & Input Data
// ──────────────────────────────────────────────────────────────────────────
{
  const s = slide();
  header(s, "Item 5", "Assumptions & Input Data");
  const top = 1.42;

  // assumptions column
  bullets(s, [
    "Deterministic seeded RNG → repeatable results (seed 101–505).",
    "Each gate lane = single server, FIFO; 2-gate map = two parallel lanes.",
    "Cars → car slots; motorcycles → moto slots; denied if no compatible slot.",
    "Search time grows with lot occupancy.",
    "No field data — ranges chosen for realistic observable behavior.",
  ], 0.45, top, 4.5, 2.1, 11.5);

  // parameter table — placed below bullets with enough room to fit on slide
  const tableTop = top + 2.3;
  const headers2 = ["Scenario", "Vehs", "Slots", "Arrival", "Entry svc", "Exit svc"];
  const colWidths = [1.85, 0.65, 0.75, 1.4, 1.1, 1.0];
  const tableW2 = colWidths.reduce((a, b) => a + b, 0);
  const cx = (W - tableW2) / 2;
  const rowH = 0.28;

  // header row
  headers2.forEach((h2, i) => {
    s.addShape(pres.shapes.RECTANGLE, {
      x: cx + colWidths.slice(0,i).reduce((a,b)=>a+b,0), y: tableTop,
      w: colWidths[i], h: rowH,
      fill: { color: NAVY }, line: { color: NAVY, width: 0 },
    });
    s.addText(h2, {
      x: cx + colWidths.slice(0,i).reduce((a,b)=>a+b,0), y: tableTop,
      w: colWidths[i], h: rowH,
      fontSize: 8.5, bold: true, color: BGWHITE, align: "center", valign: "middle", margin: 0,
    });
  });
  const tableRows = [
    ["baseline",       "44", "72", "spread",        "0.7",   "0.8"],
    ["rush_hour",      "60", "72", "clustered",      "1.0",   "0.95"],
    ["limited_slots",  "60", "16", "spread/long",    "0.75",  "0.85"],
    ["slow_entry",     "50", "72", "spread",         "3.2 ★", "0.8"],
    ["exit_congestion","52", "72", "spread",         "0.7",   "4.0 ★"],
  ];
  tableRows.forEach((row, ri) => {
    const ry = tableTop + rowH + ri * rowH;
    const bg = ri % 2 === 0 ? GRAY1 : BGWHITE;
    row.forEach((cell, ci) => {
      const isHighlight = cell.includes("★");
      s.addShape(pres.shapes.RECTANGLE, {
        x: cx + colWidths.slice(0,ci).reduce((a,b)=>a+b,0), y: ry,
        w: colWidths[ci], h: rowH,
        fill: { color: isHighlight ? "FFF3E0" : bg },
        line: { color: RULE, width: 0.5 },
      });
      s.addText(cell, {
        x: cx + colWidths.slice(0,ci).reduce((a,b)=>a+b,0), y: ry,
        w: colWidths[ci], h: rowH,
        fontSize: ci === 0 ? 8.5 : 9,
        bold: isHighlight,
        color: isHighlight ? ORANGE : (ci === 0 ? NAVY : BODY),
        align: ci === 0 ? "left" : "center", valign: "middle", margin: ci === 0 ? [0,0,0,6] : 0,
      });
    });
  });
  s.addText("★ = stressed parameter.  Map axis is orthogonal — any scenario runs on any of the 4 gate layouts.", {
    x: 0.45, y: tableTop + rowH + 5 * rowH + 0.06, w: 9.1, h: 0.22,
    fontSize: 8, italic: true, color: MUTED, margin: 0,
  });
}

// ──────────────────────────────────────────────────────────────────────────
// SLIDE 9 – Live Demo
// ──────────────────────────────────────────────────────────────────────────
{
  const s = slide(BGWHITE);
  header(s, "Item 6", "Live Demonstration");
  const top = 1.42;

  const steps2 = [
    { num: "1", title: "Start baseline / one_entrance_one_exit",
      body: "Point out: entry queue → gate → search → park → dwell → exit queue → exit." },
    { num: "2", title: "Switch to rush_hour",
      body: "Watch the entry queue spike to 55. Same capacity, clustering is the stressor." },
    { num: "3", title: "Switch to limited_slots",
      body: "Show DENIED vehicles and the denied counter. 13 denials, 100% occupancy." },
    { num: "4", title: "Switch maps (e.g. two_entrance_one_exit on slow_entry)",
      body: "Change only the map — entry wait drops 127 → 52 min. Same demand, more capacity." },
    { num: "5", title: "Custom Inputs panel",
      body: "Adjust vehicle count, slots, service times, gate count live → Apply & Run." },
  ];
  steps2.forEach((st, i) => {
    const y = top + i * 0.73;
    const bg = i % 2 === 0 ? BGLIGHT : BGWHITE;
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.45, y, w: 9.1, h: 0.63,
      fill: { color: bg }, line: { color: RULE, width: 0.8 },
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.45, y, w: 0.48, h: 0.63,
      fill: { color: BLUE }, line: { color: BLUE, width: 0 },
    });
    s.addText(st.num, {
      x: 0.45, y, w: 0.48, h: 0.63,
      fontSize: 15, bold: true, color: BGWHITE, align: "center", valign: "middle", margin: 0,
    });
    s.addText(st.title, {
      x: 1.05, y: y + 0.04, w: 8.35, h: 0.24,
      fontSize: 11.5, bold: true, color: NAVY, margin: 0,
    });
    s.addText(st.body, {
      x: 1.05, y: y + 0.3, w: 8.35, h: 0.27,
      fontSize: 10.5, color: BODY, margin: 0,
    });
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.45, y: top + 3.72, w: 9.1, h: 0.3,
    fill: { color: "FFF3E0" }, line: { color: ORANGE, width: 1 },
  });
  s.addText("⚠  Be ready to change scenario, map, or custom inputs on request — that covers 'modify inputs during questioning.'", {
    x: 0.65, y: top + 3.74, w: 8.8, h: 0.26,
    fontSize: 9.5, color: ORANGE, margin: 0,
  });
}

// ──────────────────────────────────────────────────────────────────────────
// SLIDE 10 – Results: metrics table
// ──────────────────────────────────────────────────────────────────────────
{
  const s = slide();
  header(s, "Item 7a", "Results — Five Scenarios (one_entrance_one_exit map)");
  const top = 1.4;
  const metrics = [
    "Avg entry wait (min)", "Avg exit wait (min)", "Time in system (min)",
    "Throughput (veh/hr)", "Entry gate util %", "Exit gate util %",
    "Max exit queue", "Denied vehicles",
  ];
  const scenarios = ["baseline", "rush_hour", "limited_slots", "slow_entry", "exit_congestion"];
  const data = [
    ["49.5",  "108.7", "69.0",  "127.0", "57.2"],
    ["33.7",  "37.6",  "45.0",  "5.5",   "119.0"],
    ["131.5", "195.4", "182.8", "183.5", "228.8"],
    ["9.7",   "10.0",  "7.5",   "8.4",   "6.5"],
    ["58",    "66",    "58",    "86",    "39"],
    ["80",    "85",    "80",    "69",    "89"],
    ["13",    "15",    "18",    "4",     "29"],
    ["0",     "0",     "13",    "0",     "0"],
  ];
  // highlight indices: [row, col]
  const highlights = new Set(["0,3","1,4","2,4","3,1","4,3","5,4","6,4","7,2"]);

  const cw = [2.15, 1.35, 1.35, 1.35, 1.35, 1.45];
  const allCols = ["Metric", ...scenarios];
  const totalW = cw.reduce((a,b)=>a+b,0);
  let sx = (W - totalW) / 2;

  // header row
  allCols.forEach((col, ci) => {
    s.addShape(pres.shapes.RECTANGLE, {
      x: sx + cw.slice(0,ci).reduce((a,b)=>a+b,0), y: top,
      w: cw[ci], h: 0.34,
      fill: { color: NAVY }, line: { color: NAVY, width: 0 },
    });
    s.addText(col, {
      x: sx + cw.slice(0,ci).reduce((a,b)=>a+b,0), y: top,
      w: cw[ci], h: 0.34,
      fontSize: 8.5, bold: true, color: BGWHITE, align: "center", valign: "middle", margin: 0,
    });
  });
  data.forEach((row, ri) => {
    const ry = top + 0.34 + ri * 0.35;
    const bg = ri % 2 === 0 ? GRAY1 : BGWHITE;
    // metric label
    s.addShape(pres.shapes.RECTANGLE, {
      x: sx, y: ry, w: cw[0], h: 0.35,
      fill: { color: bg }, line: { color: RULE, width: 0.5 },
    });
    s.addText(metrics[ri], {
      x: sx + 0.06, y: ry, w: cw[0] - 0.06, h: 0.35,
      fontSize: 9, color: NAVY, valign: "middle", margin: 0,
    });
    // data cells
    row.forEach((val, ci) => {
      const key = `${ri},${ci}`;
      const isHl = highlights.has(key);
      s.addShape(pres.shapes.RECTANGLE, {
        x: sx + cw[0] + cw.slice(1,ci+1).reduce((a,b)=>a+b,0), y: ry,
        w: cw[ci + 1], h: 0.35,
        fill: { color: isHl ? "FFF3E0" : bg }, line: { color: RULE, width: 0.5 },
      });
      s.addText(val, {
        x: sx + cw[0] + cw.slice(1,ci+1).reduce((a,b)=>a+b,0), y: ry,
        w: cw[ci + 1], h: 0.35,
        fontSize: isHl ? 9.5 : 9, bold: isHl, color: isHl ? ORANGE : BODY,
        align: "center", valign: "middle", margin: 0,
      });
    });
  });
  s.addText("Highlighted cells = highest / worst value per metric. Gate utilization identifies the bottleneck: ~86–89% = the limiter.", {
    x: 0.45, y: top + 3.52, w: 9.1, h: 0.25,
    fontSize: 8.5, italic: true, color: MUTED, margin: 0,
  });
}

// ──────────────────────────────────────────────────────────────────────────
// SLIDE 11 – Results: scenario comparison
// ──────────────────────────────────────────────────────────────────────────
{
  const s = slide();
  header(s, "Item 7b — Comparison 1", "Scenario Comparison", 26);
  const top = 1.42;

  // bar chart: entry wait comparison
  hBar(s,
    ["baseline", "rush_hour", "limited_slots", "slow_entry", "exit_congestion"],
    [49.5, 108.7, 69.0, 127.0, 57.2],
    [RULE, BLUE, RULE, ORANGE, RULE],
    0.45, top, 4.5, 2.2, "Avg entry wait (min)"
  );
  s.addText("Avg Entry Wait (min)", {
    x: 0.45, y: top + 2.22, w: 4.5, h: 0.22,
    fontSize: 9.5, italic: true, color: MUTED, align: "center", margin: 0,
  });

  hBar(s,
    ["baseline", "rush_hour", "limited_slots", "slow_entry", "exit_congestion"],
    [33.7, 37.6, 45.0, 5.5, 119.0],
    [RULE, RULE, RULE, RULE, ORANGE],
    5.05, top, 4.5, 2.2, "Avg exit wait (min)"
  );
  s.addText("Avg Exit Wait (min)", {
    x: 5.05, y: top + 2.22, w: 4.5, h: 0.22,
    fontSize: 9.5, italic: true, color: MUTED, align: "center", margin: 0,
  });

  // two insight boxes
  const iTop = top + 2.55;
  const insights = [
    { title: "slow_entry vs exit_congestion", body: "Same arrival load — opposite bottleneck. Entry util 86% vs Exit util 89%. Each slow gate becomes the high-util / high-wait resource while the other idles.", color: ORANGE },
    { title: "baseline vs rush_hour", body: "Same total capacity, same gate speed. Clustered arrivals push entry wait from 49→109 min and peak entry queue from 25→55. Pattern, not capacity, is the stressor.", color: BLUE },
  ];
  insights.forEach((ins, i) => {
    const x = 0.45 + i * 4.65;
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: iTop, w: 4.5, h: 0.98,
      fill: { color: BGLIGHT }, line: { color: ins.color, width: 1.5 },
    });
    s.addText(ins.title, {
      x: x + 0.12, y: iTop + 0.05, w: 4.26, h: 0.24,
      fontSize: 10, bold: true, color: ins.color, margin: 0,
    });
    s.addText(ins.body, {
      x: x + 0.12, y: iTop + 0.3, w: 4.26, h: 0.62,
      fontSize: 9.5, color: BODY, lineSpacingMultiple: 1.15, margin: 0,
    });
  });
}

// ──────────────────────────────────────────────────────────────────────────
// SLIDE 12 – Results: gate comparison (1 vs 2 cashiers)
// ──────────────────────────────────────────────────────────────────────────
{
  const s = slide();
  header(s, "Item 7b — Comparison 2", "Gate Configuration — \"One Cashier vs. Two Cashiers\"");
  const top = 1.4;

  // summary callouts row
  callout(s, 0.45, top, 2.1, 0.9, "slow_entry: +1 entry gate", "−59%", 28, BLUE);
  callout(s, 2.7,  top, 2.1, 0.9, "entry wait: 127 → 52 min",  "127→52", 20, NAVY);
  callout(s, 4.95, top, 2.1, 0.9, "exit_congestion: +1 exit gate", "−85%", 28, ORANGE);
  callout(s, 7.2,  top, 2.1, 0.9, "exit wait: 119 → 18 min",   "119→18", 20, NAVY);

  // chart: entry wait across maps for slow_entry
  hBar(s,
    ["1 entrance\n1 exit", "2 entrance\n1 exit", "1 entrance\n2 exit", "2 entrance\n2 exit"],
    [127.0, 52.1, 127.2, 52.0],
    [BLUE, "2E7D32", RULE, "2E7D32"],
    0.45, top + 1.05, 4.5, 2.0, "slow_entry: entry wait across maps"
  );
  s.addText("slow_entry — Avg Entry Wait (min) by map", {
    x: 0.45, y: top + 3.07, w: 4.5, h: 0.22,
    fontSize: 9, italic: true, color: MUTED, align: "center", margin: 0,
  });

  // chart: exit wait across maps for exit_congestion
  hBar(s,
    ["1 entrance\n1 exit", "2 entrance\n1 exit", "1 entrance\n2 exit", "2 entrance\n2 exit"],
    [119.0, 154.3, 18.2, 54.0],
    [BLUE, ORANGE, "2E7D32", "2E7D32"],
    5.05, top + 1.05, 4.5, 2.0, "exit_congestion: exit wait across maps"
  );
  s.addText("exit_congestion — Avg Exit Wait (min) by map", {
    x: 5.05, y: top + 3.07, w: 4.5, h: 0.22,
    fontSize: 9, italic: true, color: MUTED, align: "center", margin: 0,
  });

  // ⚠ note
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.45, y: top + 3.34, w: 9.1, h: 0.32,
    fill: { color: "FFF3E0" }, line: { color: ORANGE, width: 1 },
  });
  s.addText(
    "⚠  Adding a gate only helps at the bottleneck. For exit_congestion, a second entry gate made exit wait WORSE (119→154 min) — it fed the jammed exit faster.",
    { x: 0.6, y: top + 3.37, w: 8.8, h: 0.27, fontSize: 9.5, color: ORANGE, margin: 0 }
  );
}

// ──────────────────────────────────────────────────────────────────────────
// SLIDE 13 – Conclusion & Recommendations
// ──────────────────────────────────────────────────────────────────────────
{
  const s = slide(BGWHITE);
  header(s, "Item 8", "Conclusion & Recommendations");
  const top = 1.42;

  const panelH = 3.0;

  // left: findings
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.45, y: top, w: 4.45, h: panelH,
    fill: { color: BGLIGHT }, line: { color: BLUE, width: 1 },
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.45, y: top, w: 4.45, h: 0.34,
    fill: { color: BLUE }, line: { color: BLUE, width: 0 },
  });
  s.addText("Key Findings", {
    x: 0.55, y: top + 0.02, w: 4.25, h: 0.30,
    fontSize: 11, bold: true, color: BGWHITE, valign: "middle", margin: 0,
  });
  bullets(s, [
    "Gate utilization identifies the bottleneck (~86–89% = the limiter).",
    "Arrival clustering inflates waits even with adequate capacity.",
    "Parking capacity is a separate constraint — causes denials regardless of gate speed.",
    "Adding a gate lane only helps at the bottleneck; adding it elsewhere can make things worse.",
  ], 0.58, top + 0.44, 4.18, panelH - 0.5, 11.5);

  // right: recommendations
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.1, y: top, w: 4.45, h: panelH,
    fill: { color: BGLIGHT }, line: { color: NAVY, width: 1 },
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.1, y: top, w: 4.45, h: 0.34,
    fill: { color: NAVY }, line: { color: NAVY, width: 0 },
  });
  s.addText("Recommendations", {
    x: 5.2, y: top + 0.02, w: 4.25, h: 0.30,
    fontSize: 11, bold: true, color: BGWHITE, valign: "middle", margin: 0,
  });
  bullets(s, [
    "Add a second lane at the bottleneck gate (entry for arrival surges; exit for end-of-day congestion). Use gate utilization to decide which.",
    "Stagger demand (e.g., off-peak promotions) to flatten arrival clusters.",
    "Match usable capacity to demand to cut denials.",
    "Future work: multiple replications with confidence intervals; CSV export; in-UI gate/arrival editing.",
  ], 5.23, top + 0.44, 4.18, panelH - 0.5, 11.5);
}

// ──────────────────────────────────────────────────────────────────────────
// SLIDE 14 – Q&A / Thank You
// ──────────────────────────────────────────────────────────────────────────
{
  const s = slide(BGWHITE);
  // light accent rule (no dark bars)
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.45, y: 0.8, w: 9.1, h: 0.04, fill: { color: RULE }, line: { color: RULE, width: 0 },
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.45, y: H - 0.4, w: 9.1, h: 0.04, fill: { color: RULE }, line: { color: RULE, width: 0 },
  });
  s.addText("Thank You", {
    x: 1, y: 1.0, w: 8, h: 1.0,
    fontSize: 48, bold: true, color: NAVY, align: "center", margin: 0,
  });
  s.addText("Questions?", {
    x: 1, y: 2.0, w: 8, h: 0.55,
    fontSize: 26, italic: true, color: BLUE, align: "center", margin: 0,
  });

  // cheat-sheet row
  const cx2 = 0.45, cy = 2.85, cw2 = 2.15, ch = 0.8;
  const chips = [
    { lbl: "slow_entry bottleneck", val: "entry wait 127→52 min\n+1 entry gate" },
    { lbl: "exit_congestion bottleneck", val: "exit wait 119→18 min\n+1 exit gate → 2× throughput" },
    { lbl: "rush_hour 2×2 map", val: "throughput 10→17.3 veh/hr\n(+72%)" },
    { lbl: "limited_slots", val: "13 denied vehicles\n100% occupancy" },
  ];
  chips.forEach((chip, i) => {
    const x = cx2 + i * (cw2 + 0.15);
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: cy, w: cw2, h: ch,
      fill: { color: BGLIGHT }, line: { color: RULE, width: 1 },
    });
    s.addText(chip.lbl, {
      x: x + 0.08, y: cy + 0.06, w: cw2 - 0.16, h: 0.24,
      fontSize: 8, bold: true, color: NAVY, align: "center", margin: 0,
    });
    s.addText(chip.val, {
      x: x + 0.08, y: cy + 0.32, w: cw2 - 0.16, h: 0.42,
      fontSize: 9, color: BODY, align: "center", lineSpacingMultiple: 1.2, margin: 0,
    });
  });
  s.addText("86 automated tests passing  ·  python3 -m unittest", {
    x: 0.5, y: 4.9, w: 9, h: 0.25,
    fontSize: 8.5, color: MUTED, align: "center", italic: true, margin: 0,
  });
}

// ── write file ─────────────────────────────────────────────────────────────
const outPath = path.join(__dirname, "CSE10L-Parking-Simulation-Final.pptx");
pres.writeFile({ fileName: outPath })
  .then(() => console.log("Wrote", outPath))
  .catch(e => { console.error(e); process.exit(1); });
