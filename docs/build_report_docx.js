// Generates docs/REPORT.docx from the report content.
// Run: NODE_PATH=$(npm root -g) node docs/build_report_docx.js
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
  ShadingType, TableOfContents, PageNumber, PageBreak, Header, Footer,
  VerticalAlign,
} = require("docx");

// ---- palette / sizing ----------------------------------------------------
const ACCENT = "1F4E79";   // deep blue
const ACCENT2 = "2E75B6";  // lighter blue
const HEADER_FILL = "1F4E79";
const ZEBRA = "EDF2F8";
const HILITE = "FCE9D6";    // soft amber for emphasized cells
const CONTENT_WIDTH = 9360; // US Letter, 1" margins

const cellBorder = { style: BorderStyle.SINGLE, size: 1, color: "C7D2DD" };
const cellBorders = { top: cellBorder, bottom: cellBorder, left: cellBorder, right: cellBorder };
const cellMargins = { top: 60, bottom: 60, left: 110, right: 110 };

// ---- helpers -------------------------------------------------------------
function body(text, opts = {}) {
  return new Paragraph({
    spacing: { after: 120, line: 276 },
    children: parseInline(text),
    ...opts,
  });
}

// parse **bold** and `code` inline markers into TextRuns
function parseInline(text, base = {}) {
  const runs = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let last = 0, m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) runs.push(new TextRun({ text: text.slice(last, m.index), ...base }));
    const tok = m[0];
    if (tok.startsWith("**")) {
      runs.push(new TextRun({ text: tok.slice(2, -2), bold: true, ...base }));
    } else {
      runs.push(new TextRun({ text: tok.slice(1, -1), font: "Consolas", ...base }));
    }
    last = re.lastIndex;
  }
  if (last < text.length) runs.push(new TextRun({ text: text.slice(last), ...base }));
  return runs.length ? runs : [new TextRun({ text, ...base })];
}

function h1(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(text)] });
}
function h2(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(text)] });
}
function bullet(text) {
  return new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 }, children: parseInline(text) });
}
function numbered(text, ref = "nums") {
  return new Paragraph({ numbering: { reference: ref, level: 0 }, spacing: { after: 60 }, children: parseInline(text) });
}

// Build a table. rows = array of arrays of strings. First row = header.
// emphasize: set of "r,c" keys to highlight; colWidths: array summing to CONTENT_WIDTH.
function makeTable(rows, colWidths, emphasize = new Set()) {
  const trs = rows.map((cells, r) => new TableRow({
    tableHeader: r === 0,
    children: cells.map((val, c) => {
      const isHeader = r === 0;
      const key = `${r},${c}`;
      const fill = isHeader ? HEADER_FILL : (emphasize.has(key) ? HILITE : (r % 2 === 0 ? ZEBRA : "FFFFFF"));
      return new TableCell({
        borders: cellBorders,
        width: { size: colWidths[c], type: WidthType.DXA },
        margins: cellMargins,
        verticalAlign: VerticalAlign.CENTER,
        shading: { fill, type: ShadingType.CLEAR },
        children: [new Paragraph({
          alignment: c === 0 ? AlignmentType.LEFT : AlignmentType.CENTER,
          spacing: { after: 0, line: 252 },
          children: parseInline(val, isHeader ? { bold: true, color: "FFFFFF" } : {}),
        })],
      });
    }),
  }));
  return new Table({ width: { size: CONTENT_WIDTH, type: WidthType.DXA }, columnWidths: colWidths, rows: trs });
}

function caption(text) {
  return new Paragraph({
    spacing: { before: 60, after: 200 },
    children: [new TextRun({ text, italics: true, size: 18, color: "5A6B7B" })],
  });
}

function ruleAfter() {
  return new Paragraph({
    spacing: { before: 80, after: 200 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: ACCENT2, space: 1 } },
    children: [new TextRun("")],
  });
}

// ---- cover page ----------------------------------------------------------
function coverField(label, value) {
  return new Paragraph({
    spacing: { after: 80 },
    children: [
      new TextRun({ text: label + "  ", bold: true, color: ACCENT }),
      new TextRun({ text: value, color: "333333" }),
    ],
  });
}

const cover = [
  new Paragraph({ spacing: { before: 1400, after: 0 }, alignment: AlignmentType.CENTER,
    border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: ACCENT, space: 8 } },
    children: [new TextRun({ text: "MALL PARKING FLOW", bold: true, size: 56, color: ACCENT })] }),
  new Paragraph({ spacing: { before: 200, after: 80 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "A Discrete-Event Simulation of Entry, Parking & Exit Congestion", italics: true, size: 28, color: "444444" })] }),
  new Paragraph({ spacing: { before: 600, after: 80 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Final Project Report", bold: true, size: 30 })] }),
  new Paragraph({ spacing: { after: 700 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "CSE 10/L – Modeling and Simulation", size: 26, color: ACCENT2 })] }),
  coverField("Group Members:", "________________________________________"),
  new Paragraph({ spacing: { after: 80 }, children: [new TextRun({ text: "                                ________________________________________", color: "333333" })] }),
  new Paragraph({ spacing: { after: 80 }, children: [new TextRun({ text: "                                ________________________________________", color: "333333" })] }),
  coverField("Instructor:", "________________________________________"),
  coverField("Section:", "____________________"),
  coverField("Date:", "____________________"),
  new Paragraph({ spacing: { before: 900 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Department of Arts and Sciences Education · Computer Science Program", size: 18, color: "777777" })] }),
  new Paragraph({ alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "UM Visayan Campus, Visayan Village, Tagum City, Davao del Norte", size: 18, color: "777777" })] }),
  new Paragraph({ children: [new PageBreak()] }),
];

// ---- TOC -----------------------------------------------------------------
const toc = [
  new Paragraph({ spacing: { after: 160 }, children: [new TextRun({ text: "Table of Contents", bold: true, size: 32, color: ACCENT })] }),
  new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-2" }),
  new Paragraph({ children: [new PageBreak()] }),
];

// ============================ CONTENT =====================================
const content = [];
const P = (...x) => content.push(...x);

// 1. Introduction
P(h1("1. Introduction"));
P(body("**Project title:** Mall Parking Flow — A Discrete-Event Simulation of Entry, Parking, and Exit Congestion."));
P(body("**Background.** A mall parking lot is a queuing system. Vehicles arrive over time, wait at an **entry gate**, search for and occupy a **parking slot**, dwell while their drivers shop, and later queue at an **exit gate** to leave. Each gate lane can serve only one vehicle at a time, and the lot has finite capacity, so congestion (queues) forms whenever demand outpaces service."));
P(body("This project models that system with **discrete-event simulation (DES)** using Python + **SimPy**, and visualizes it in a top-down browser dashboard so the behavior can be observed over time and measured. The system is configured along two independent axes:"));
P(bullet("**Scenario (demand profile)** — how busy the lot is and how fast gates serve: number of vehicles, arrival pattern, usable slots, and entry/exit service times."));
P(bullet("**Map (gate layout)** — the physical lot: how many entry gates and exit gates exist (1 or 2 of each). The map sets the gate resource capacity; the scenario sets the load on it."));
P(body("Separating these axes lets us answer the classic operations question — “one cashier vs. two cashiers?” — by running the same demand on a one-gate map and a two-gate map and comparing."));
P(body("**Importance.** Parking congestion affects customer experience, safety, and mall throughput. Simulation lets us test “what if” changes (more demand, fewer slots, slower gates, an extra gate lane) without rebuilding the real lot, and quantify their impact on waiting time, queue length, throughput, and resource utilization."));
P(ruleAfter());

// 2. Problem Definition
P(h1("2. Problem Definition"));
P(body("**Problem.** Mall visitors experience delays at two bottlenecks: the **entry gate** (a queue builds when arrivals cluster or the gate is slow) and the **exit gate** (a queue builds when many vehicles leave at once or exit processing is slow). When the lot is full, vehicles are **denied** entry entirely."));
P(body("**Why it matters.** Long waits frustrate customers and can spill back onto public roads; denials represent lost visits. Management needs to know which bottleneck dominates under different conditions, how sensitive waiting time is to capacity and gate speed, and whether adding a second gate lane is worth it."));
P(body("**What the simulation analyzes.** For each operating condition (a scenario run on a chosen map), the model measures average waiting time, queue lengths, throughput, gate utilization, and processing time, and lets us compare conditions to identify the limiting resource and the effect of adding gate capacity."));
P(ruleAfter());

// 3. Objectives
P(h1("3. Objectives"));
P(numbered("**Analyze queue performance** at the entry and exit gates (waiting time and queue length)."));
P(numbered("**Measure resource utilization** of the entry gate(s), exit gate(s), and parking capacity."));
P(numbered("**Quantify throughput** (vehicles completed per hour) and total time-in-system."));
P(numbered("**Compare operational scenarios** — different arrival patterns, reduced capacity, slow entry service, and slow exit service — to identify and explain the dominant bottleneck in each."));
P(numbered("**Compare gate configurations** — run the same demand on one-gate vs. two-gate maps to measure the benefit of adding an entry or exit lane (“one cashier vs. two cashiers”)."));
P(ruleAfter());

// 4. System Model and Design
P(h1("4. System Model and Design"));
P(body("**Simulation type:** discrete-event, single replication per (scenario × map), deterministic (seeded RNG)."));
P(makeTable([
  ["DES element", "In this model"],
  ["Entities", "Vehicles (cars and motorcycles), each with an arrival time, a type, and — on multi-gate maps — an assigned entrance/exit lane."],
  ["Events", "Arrival, join entry queue, entry-gate service start/end, gate crossing, slot search start/end (park), dwell end (exit request), exit-gate service start/end, gate crossing, departure (done)."],
  ["Resources", "Entry gate(s) (simpy.Resource, capacity = entry-gate count), exit gate(s) (one resource per exit lane), and parking slots (typed pools: car slots and motorcycle slots)."],
  ["Queues", "Entry queue(s) (FIFO before each entry gate) and exit queue(s) (FIFO before each exit gate)."],
  ["State variables", "Per-vehicle state (11 states), number queued at each gate, slots occupied / free / targeted, denied count, completed count, simulation clock."],
], [1900, 7460]));
P(caption("Table 1. Discrete-event model elements."));
P(h2("Two configuration axes"));
P(bullet("**Scenario** selects a demand profile (vehicles, arrival pattern, usable slots, entry/exit service times). Five scenarios are provided (see Section 5)."));
P(bullet("**Map** selects a gate layout. Four maps are formed by crossing {1, 2} entry gates with {1, 2} exit gates: `one_entrance_one_exit`, `two_entrance_one_exit`, `one_entrance_two_exit`, `two_entrance_two_exit`. The map sets the SimPy resource capacity at each gate and the background image; a two-gate map splits arrivals/departures across two lanes."));
P(h2("Vehicle lifecycle (state machine)"));
P(body("`scheduled → entry_queue → approaching_gate → gate_wait → gate_crossing → searching → parked → exit_queue → exiting → done`, with a **denied** branch (`gate_crossing → denied → exit_queue → … → done`) when no compatible slot is free. The full flowchart is in flowchart.md; the conceptual architecture is in architecture.md."));
P(body("**Behavior over time.** The server runs one full simulation per (scenario, map) and records a timeline of frames (snapshots every 0.05 simulated minutes). The browser replays the frames, so reviewers watch queues form and drain, slots fill, and gates open/close, while summary metrics are computed from the per-vehicle event timestamps."));
P(body("**Implementation:** `app/simulation.py` (model, paths, metrics), `app/api.py` (JSON API), `app/static/` (dashboard)."));
P(ruleAfter());

// 5. Assumptions and Input Data
P(h1("5. Assumptions and Input Data"));
P(h2("Assumptions"));
P(bullet("One deterministic, seeded run represents each scenario, so results are repeatable for review and testing (different seeds would give one sample of natural variation)."));
P(bullet("Each gate lane serves one vehicle at a time (capacity 1 per lane); queue discipline is FIFO. A two-gate map = two parallel single-server lanes."));
P(bullet("Cars use car slots; motorcycles use motorcycle slots; a vehicle is **denied** if no compatible slot is free when it reaches the gate."));
P(bullet("On multi-gate maps, arriving/departing vehicles are split evenly (alternating) across the two lanes."));
P(bullet("Vehicles follow fixed, readable lanes (the model abstracts away free-form driving physics)."));
P(bullet("Search time grows with occupancy (a fuller lot takes longer to find a space)."));
P(h2("Basis of input data"));
P(body("No field data was available, so arrival times and service/dwell times are generated from a seeded RNG within ranges chosen to produce realistic, observable mall behavior. Each scenario changes only a few parameters from the baseline:"));
P(makeTable([
  ["Scenario", "Vehicles", "Usable slots", "Arrival pattern", "Entry svc (min)", "Exit svc (min)"],
  ["baseline", "44", "72", "spread", "0.7", "0.8"],
  ["rush_hour", "60", "72", "clustered (early wave)", "1.0", "0.95"],
  ["limited_slots", "60", "16 (of 72 drawn)", "spread, long dwell", "0.75", "0.85"],
  ["slow_entry", "50", "72", "spread", "**3.2**", "0.8"],
  ["exit_congestion", "52", "72", "spread", "0.7", "**4.0**"],
], [1900, 1160, 1700, 2000, 1300, 1300], new Set(["4,4", "5,5"])));
P(caption("Table 2. Per-scenario demand parameters. Seeds: 101 / 202 / 303 / 404 / 505. The map axis is orthogonal — any scenario can run on any of the four gate layouts."));
P(body("Service time per vehicle = a base service value + a small random component; dwell (shopping) time is drawn from a per-scenario range."));
P(body("**Constraints and limitations.** Local class MVP (not deployed); single replication (no confidence intervals); fixed lane geometry; per-lane gate capacity fixed at 1; no pricing/payment modeling."));
P(ruleAfter());

// 7. Experimental Results and Analysis
P(h1("7. Experimental Results and Analysis"));
P(body("All runs are deterministic seeded results, produced by `app/simulation.py` and reproducible from the dashboard’s “Compare scenarios” view (which generates the table and bar charts live for a chosen map)."));
P(h2("7.1 Five scenarios on the base map (one_entrance_one_exit)"));
P(makeTable([
  ["Metric", "baseline", "rush_hour", "limited_slots", "slow_entry", "exit_congestion"],
  ["Avg entry wait (min)", "49.5", "108.7", "69.0", "**127.0**", "57.2"],
  ["Avg exit wait (min)", "33.7", "37.6", "45.0", "5.5", "**119.0**"],
  ["Avg time in system (min)", "131.5", "195.4", "182.8", "183.5", "**228.8**"],
  ["Entry service (min)", "1.75", "2.09", "1.81", "**4.27**", "1.75"],
  ["Exit service (min)", "0.98", "1.10", "1.02", "0.94", "**4.19**"],
  ["Throughput (veh/hr)", "9.7", "**10.0**", "7.5", "8.4", "6.5"],
  ["Entry gate util (%)", "58.0", "65.7", "58.4", "**86.0**", "39.3"],
  ["Exit gate util (%)", "80.2", "85.1", "79.9", "69.3", "**89.3**"],
  ["Avg entry queue", "8.0", "18.1", "11.0", "17.8", "6.2"],
  ["Avg exit queue", "5.4", "6.3", "7.2", "0.8", "**13.0**"],
  ["Max entry queue", "25", "**55**", "42", "40", "35"],
  ["Max exit queue", "13", "15", "18", "4", "**29**"],
  ["Denied vehicles", "0", "0", "**13**", "0", "0"],
], [2360, 1400, 1400, 1400, 1400, 1400],
  new Set(["1,4","2,5","3,5","4,4","5,5","6,2","7,4","8,5","10,5","11,2","12,5","13,3"])));
P(caption("Table 3. Five scenarios on the base one-gate map (deterministic seeded results)."));
P(body("**Interpretation**"));
P(bullet("**baseline** — balanced: moderate waits, ~80% exit-gate utilization, no denials. Reference point."));
P(bullet("**rush_hour** — clustered arrivals more than double the entry wait (49→109 min) and push the entry queue to a peak of 55. The single gate still clears everyone, so throughput is highest (10/hr): the demand pattern, not capacity, is the stressor."));
P(bullet("**limited_slots** — cutting usable capacity from 72 to 16 causes 13 denials and lowers throughput (7.5/hr); the binding constraint is parking capacity, not the gates."));
P(bullet("**slow_entry** — a slow entry gate drives entry-gate utilization to 86% and the highest entry wait (127 min), while the exit side stays idle (exit wait 5.5 min). Classic single-server bottleneck at the entrance."));
P(bullet("**exit_congestion** — a slow exit gate pushes exit-gate utilization to 89%, the largest exit queue (peak 29), and the longest time-in-system (229 min). The bottleneck is the exit."));
P(body("**Scenario comparison (≥2 scenarios).** Contrasting **slow_entry vs. exit_congestion** isolates the two bottlenecks at equal arrival load: the slow gate in each case becomes the high-utilization, high-wait resource while the other gate is underused. Contrasting **baseline vs. rush_hour** shows that the same resources produce very different queues purely from arrival clustering."));

P(h2("7.2 Gate-configuration comparison — “one cashier vs. two cashiers”"));
P(body("Here the demand is held fixed and only the map (gate count) changes. This is the direct analogue of the rubric’s “one cashier vs. two cashiers” example."));
P(body("**slow_entry (entry is the bottleneck) — adding a second entry gate:**"));
P(makeTable([
  ["Map", "Entry gates", "Avg entry wait", "Entry util %", "Throughput (veh/hr)", "Time in system"],
  ["one_entrance_one_exit", "1", "**127.0**", "86.0", "8.4", "183.5"],
  ["two_entrance_one_exit", "2", "**52.1**", "51.0", "10.0", "151.3"],
], [2700, 1300, 1500, 1300, 1560, 1000], new Set(["1,2","2,2"])));
P(caption("Table 4. slow_entry: a second entry lane cuts the entry wait ~59% (127→52 min) and raises throughput. Adding an exit gate instead does almost nothing — capacity must go at the bottleneck."));
P(body("**exit_congestion (exit is the bottleneck) — adding a second exit gate:**"));
P(makeTable([
  ["Map", "Exit gates", "Avg exit wait", "Exit util %", "Throughput (veh/hr)", "Time in system"],
  ["one_entrance_one_exit", "1", "**119.0**", "89.3", "6.5", "228.8"],
  ["one_entrance_two_exit", "2", "**18.2**", "77.9", "11.4", "127.2"],
], [2700, 1300, 1500, 1300, 1560, 1000], new Set(["1,2","2,2","1,4","2,4"])));
P(caption("Table 5. exit_congestion: a second exit lane cuts the exit wait ~85% (119→18 min) and nearly doubles throughput. Adding a second entry gate instead makes exit congestion worse (119→154 min) — moving the bottleneck."));
P(body("**rush_hour — full two-by-two map (two entry + two exit):**"));
P(makeTable([
  ["Map", "Entry / Exit gates", "Throughput (veh/hr)", "Time in system", "Max entry queue"],
  ["one_entrance_one_exit", "1 / 1", "10.0", "195.4", "55"],
  ["two_entrance_two_exit", "2 / 2", "**17.3**", "**118.7**", "50"],
], [2900, 1900, 1860, 1500, 1200], new Set(["2,2","2,3"])));
P(caption("Table 6. rush_hour: doubling both gates lifts throughput +72% (10.0→17.3/hr) and cuts time-in-system ~39%."));
P(ruleAfter());

// 8. Conclusion and Recommendations
P(h1("8. Conclusion and Recommendations"));
P(h2("Key findings"));
P(bullet("The system has two independent bottlenecks (entry and exit gates); which one dominates depends on the scenario, and **gate utilization** cleanly identifies it (the ~86–89% gate is the limiter)."));
P(bullet("Arrival **clustering** (rush hour) inflates waiting time even when total capacity is adequate."));
P(bullet("**Parking capacity** is a separate constraint: when slots are scarce, vehicles are denied and throughput drops regardless of gate speed."));
P(bullet("**Adding a gate lane only helps at the bottleneck.** A second entry gate cut the slow-entry wait 127→52 min; a second exit gate cut the exit-congestion wait 119→18 min and doubled throughput. Adding capacity at the non-bottleneck gate gave little or no benefit — and in exit_congestion a second entry gate made things worse by feeding the jammed exit faster."));
P(h2("Recommendations"));
P(bullet("**Add a second lane at whichever gate is the bottleneck** for the expected pattern (a second entry gate for rush-hour entry surges; a second exit gate for end-of-day exit surges). Use gate utilization to decide which."));
P(bullet("**Stagger demand** (e.g., promotions outside peak) to flatten arrival clusters."));
P(bullet("Ensure usable capacity matches demand to avoid denials."));
P(h2("Future work"));
P(body("Multiple replications with confidence intervals, in-UI editing of arrival rates and gate counts beyond the four preset maps, and CSV export of metrics for offline analysis."));
P(new Paragraph({ spacing: { before: 200 }, children: [new TextRun({ text: "Reproducibility: results above are deterministic. Regenerate them from the dashboard “Compare scenarios” view or by running app/simulation.py directly. The behavior is covered by an automated test suite (python3 -m unittest, 86 tests passing).", italics: true, size: 18, color: "5A6B7B" })] }));

// ---- document ------------------------------------------------------------
const doc = new Document({
  creator: "CSE 10/L Group",
  title: "Mall Parking Flow — Final Project Report",
  styles: {
    default: { document: { run: { font: "Calibri", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 30, bold: true, color: ACCENT, font: "Calibri" },
        paragraph: { spacing: { before: 280, after: 140 }, outlineLevel: 0,
          border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "C7D2DD", space: 4 } } } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 25, bold: true, color: ACCENT2, font: "Calibri" },
        paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 1 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 540, hanging: 280 } } } }] },
      { reference: "nums", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 540, hanging: 280 } } } }] },
    ],
  },
  sections: [
    // Cover (no header/footer)
    { properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
      children: cover },
    // TOC + body (with footer page numbers)
    { properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
      footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
        children: [
          new TextRun({ text: "Mall Parking Flow — CSE 10/L    ·    Page ", size: 16, color: "888888" }),
          new TextRun({ children: [PageNumber.CURRENT], size: 16, color: "888888" }),
        ] })] }) },
      children: [...toc, ...content] },
  ],
});

Packer.toBuffer(doc).then((buffer) => {
  const out = path.join(__dirname, "REPORT.docx");
  fs.writeFileSync(out, buffer);
  console.log("Wrote", out, buffer.length, "bytes");
});
