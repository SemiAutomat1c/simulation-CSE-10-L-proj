# Presentation Slides — Content

Full slide-by-slide content for the CSE 10/L final presentation. Copy each block into your slide
tool (Google Slides / PowerPoint / Canva). Target: **15–20 min** presentation + demo, then
**5–10 min** Q&A. Diagrams: screenshot the Mermaid charts from [`flowchart.md`](flowchart.md) and
[`architecture.md`](architecture.md); figures come from [`REPORT.md`](REPORT.md); the live demo
runs from the dashboard.

> Legend: **Title** = slide title · • = on-slide bullet · _Notes:_ = what the speaker says.

---

## Slide 1 — Title  *(rubric: cover)*

**Mall Parking Flow**
*A Discrete-Event Simulation of Entry, Parking & Exit Congestion*

• CSE 10/L – Modeling and Simulation
• Group members: ________________________
• Instructor: ________________  ·  Section: ______  ·  Date: ______

_Notes:_ One line — "We simulated a mall parking lot as a queuing system to find and fix its
bottlenecks."

---

## Slide 2 — Introduction  *(item 1)*

**A parking lot is a queuing system**

• Vehicles **arrive** → wait at an **entry gate** → **search & park** → **shop (dwell)** → queue at
  an **exit gate** → leave.
• Each gate lane serves one vehicle at a time; the lot has finite slots.
• Congestion (queues) forms whenever **demand outpaces service**.
• Built with **Python + SimPy** (discrete-event simulation) and a **top-down browser dashboard**.

_Notes:_ Frame it as the same math as a bank or supermarket checkout — arrivals, servers, queues —
just applied to cars and parking spaces.

---

## Slide 3 — Problem Definition  *(item 2)*

**Two bottlenecks + denials**

• **Entry gate** — queue builds when arrivals cluster or the gate is slow.
• **Exit gate** — queue builds when many leave at once or exit processing is slow.
• **Denials** — when the lot is full, vehicles can't park at all (lost visits).

**Why it matters:** long waits hurt customer experience, can spill onto public roads, and denials
= lost business. Management needs to know *which* bottleneck dominates and whether a second gate
lane is worth it.

_Notes:_ Emphasize the management question we'll answer with data: "one cashier vs. two cashiers?"

---

## Slide 4 — Objectives  *(item 3)*

**What the simulation measures & compares**

1. **Analyze queue performance** — waiting time and queue length at each gate.
2. **Measure resource utilization** — entry gate, exit gate, parking capacity.
3. **Quantify throughput** — vehicles completed per hour + total time-in-system.
4. **Compare scenarios** — arrival patterns, capacity, slow entry, slow exit → find the bottleneck.
5. **Compare gate configurations** — same demand, 1 vs. 2 gates ("one cashier vs. two cashiers").

_Notes:_ Objectives 4 and 5 are the two required comparisons — flag them now.

---

## Slide 5 — System Model: DES elements  *(item 4a)*

**Entities · Events · Resources · Queues · State**

| Element | In this model |
| --- | --- |
| **Entities** | Vehicles (cars & motorcycles); each has arrival time, type, assigned lane |
| **Events** | arrival, gate service start/end, gate crossing, search/park, exit request, departure |
| **Resources** | Entry gate(s), exit gate(s) (`simpy.Resource`), typed parking slot pools |
| **Queues** | Entry queue(s) + exit queue(s), FIFO |
| **State** | per-vehicle state ×11, queue lengths, slots free/occupied, denied/completed, clock |

→ *Insert the conceptual diagram from `architecture.md`.*

_Notes:_ Point at the diagram: entities flow left→right through resources; gates and slots update
the state variables we later measure.

---

## Slide 6 — System Model: two configuration axes  *(item 4a, the updated design)*

**Scenario (demand) × Map (gate layout) — independent axes**

• **Scenario** = how busy + how fast: vehicles, arrival pattern, usable slots, service times.
  *(baseline, rush_hour, limited_slots, slow_entry, exit_congestion)*
• **Map** = the physical lot: how many gates exist. Map sets gate **resource capacity**.

| Map | Entry gates | Exit gates |
| --- | --- | --- |
| `one_entrance_one_exit` | 1 | 1 |
| `two_entrance_one_exit` | 2 | 1 |
| `one_entrance_two_exit` | 1 | 2 |
| `two_entrance_two_exit` | 2 | 2 |

→ Same demand on a 1-gate vs. 2-gate map = a clean controlled experiment.

_Notes:_ This separation is the key design idea: the scenario is the *load*, the map is the
*capacity*. We can vary one while holding the other fixed.

---

## Slide 7 — Process Flow  *(item 4b)*

**Vehicle lifecycle (11 states)**

→ *Insert the flowchart from `flowchart.md`.*

`scheduled → entry_queue → approaching_gate → gate_wait → gate_crossing → searching → parked →
exit_queue → exiting → done`  — plus a **denied** branch when no compatible slot is free.

• Entry gate held: approach → cross. · Exit gate held: service → merge. · Slot held: reserve → release.

_Notes:_ Walk one car through the diagram once, end-to-end, including the denied branch.

---

## Slide 8 — Assumptions & Input Data  *(item 5)*

**Seeded, repeatable, justified (no field data → reasoned assumptions)**

• Deterministic seeded RNG → repeatable results for review & testing.
• Each gate lane = single server, FIFO; a 2-gate map = two parallel lanes.
• Cars→car slots, motorcycles→moto slots; **denied** if no compatible slot.
• Search time grows with occupancy.

| Scenario | Vehicles | Usable slots | Arrival | Entry svc | Exit svc |
| --- | --- | --- | --- | --- | --- |
| baseline | 44 | 72 | spread | 0.7 | 0.8 |
| rush_hour | 60 | 72 | clustered | 1.0 | 0.95 |
| limited_slots | 60 | 16 | spread, long dwell | 0.75 | 0.85 |
| slow_entry | 50 | 72 | spread | **3.2** | 0.8 |
| exit_congestion | 52 | 72 | spread | 0.7 | **4.0** |

_Notes:_ The map axis is orthogonal — any scenario runs on any of the 4 layouts.

---

## Slide 9 — LIVE DEMO  *(item 6)*

**Run it: `python3 -m uvicorn app.main:app` → open the dashboard**

• Start on **baseline / one_entrance_one_exit** — point out: entry queue → gate → search → park →
  dwell → exit queue → exit.
• Switch to **rush_hour** — watch the entry queue spike.
• Switch to **limited_slots** — show **denied** vehicles + the denied counter.
• Use the **speed slider / replay**; open the **Custom Inputs** panel.

_Notes:_ Narrate the state colors as cars move. **Be ready to change scenario/map on request — that
covers "modify inputs during questioning."**

---

## Slide 10 — Results: metrics on one map  *(item 7a)*

**Five scenarios · `one_entrance_one_exit`** (entry/exit wait min · util % · throughput veh/hr)

| Metric | baseline | rush_hour | limited_slots | slow_entry | exit_congestion |
| --- | --- | --- | --- | --- | --- |
| Avg entry wait | 49.5 | 108.7 | 69.0 | **127.0** | 57.2 |
| Avg exit wait | 33.7 | 37.6 | 45.0 | 5.5 | **119.0** |
| Time in system | 131.5 | 195.4 | 182.8 | 183.5 | **228.8** |
| Throughput | 9.7 | 10.0 | 7.5 | 8.4 | 6.5 |
| Entry util % | 58 | 66 | 58 | **86** | 39 |
| Exit util % | 80 | 85 | 80 | 69 | **89** |
| Max exit queue | 13 | 15 | 18 | 4 | **29** |
| Denied | 0 | 0 | **13** | 0 | 0 |

_Notes:_ **Utilization finds the bottleneck** — the ~86–89% gate is the limiter in each stressed
scenario. limited_slots is a *capacity* problem (denials), not a gate problem.

---

## Slide 11 — Results: scenario comparison  *(item 7b — required comparison #1)*

**slow_entry vs. exit_congestion — same load, opposite bottleneck**

• **slow_entry:** entry util **86%**, entry wait **127 min**, exit idle (5.5 min).
• **exit_congestion:** exit util **89%**, exit wait **119 min**, longest time-in-system **229 min**.
• **baseline vs. rush_hour:** *same resources*, but clustering pushes entry wait 49→109 and the
  entry queue to a peak of **55** — arrival pattern alone creates congestion.

_Notes:_ The slow gate becomes the high-util / high-wait resource while the other sits underused —
the definition of a bottleneck.

---

## Slide 12 — Results: gate comparison  *(item 7b — required comparison #2: "1 vs 2 cashiers")*

**Hold demand fixed, change only the map (gate count)**

| Demand | Change | Result |
| --- | --- | --- |
| **slow_entry** | +1 **entry** gate (1→2) | entry wait **127 → 52 min** (−59%); throughput 8.4→10.0 |
| **exit_congestion** | +1 **exit** gate (1→2) | exit wait **119 → 18 min** (−85%); throughput **6.5 → 11.4** |
| **rush_hour** | 1×1 → 2×2 gates | throughput **10.0 → 17.3 veh/hr** (+72%); time-in-system −39% |

⚠ **Adding the gate only helps at the bottleneck.** For exit_congestion, adding a second *entry*
gate instead made exit wait **worse** (119→154 min) — it just fed the jam faster.

_Notes:_ This is the headline result. Capacity must go **where the queue is**, and utilization
tells you where that is.

---

## Slide 13 — Conclusion & Recommendations  *(item 8)*

**Findings**
• Two independent bottlenecks; **gate utilization identifies the limiter** (~86–89%).
• Arrival **clustering** inflates waits even with adequate capacity.
• **Parking capacity** is a separate constraint (denials when slots are scarce).
• **A second gate lane helps only at the bottleneck** — and can backfire elsewhere.

**Recommendations**
• Add a second lane at the **bottleneck gate** (entry for arrival surges, exit for end-of-day).
• **Stagger demand** to flatten arrival clusters. · Match usable capacity to demand to cut denials.

_Notes:_ Tie every recommendation back to a number on slides 10–12.

---

## Slide 14 — Q&A / Thank you

**Thank you — questions?**

• Repo: ______________________
• Reproducible, deterministic results · automated tests: `python3 -m unittest` → **86 passing**.
• Ready to change scenarios, maps, and custom inputs live.

_Notes:_ Future work: multiple replications + confidence intervals, in-UI gate/arrival editing,
CSV export.

---

## Demo cheat-sheet (headline numbers)

- **slow_entry** → entry wait **127 min**, entry util **86%**; +1 entry gate → **52 min**.
- **exit_congestion** → exit wait **119 min**, exit util **89%**, max exit queue **29**; +1 exit gate → **18 min**, throughput **6.5→11.4**.
- **rush_hour** → max entry queue **55**, throughput **10/hr**; on 2×2 map → **17.3/hr**.
- **limited_slots** → **13 denied**, 100% occupancy.
- Map axis: `one_entrance_one_exit` / `two_entrance_one_exit` / `one_entrance_two_exit` / `two_entrance_two_exit`.
