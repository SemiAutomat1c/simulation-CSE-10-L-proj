# Mall Parking Flow — Discrete-Event Simulation
### CSE 10/L – Modeling and Simulation · Final Project Report

> **PDF export note:** Add a front cover page (project title, course, section, group
> members, instructor, date) before exporting this file to PDF. This document covers
> the required report items **1, 2, 3, 4, 5, 7** (and 8). Diagrams for item 4 are in
> [`flowchart.md`](flowchart.md) and [`architecture.md`](architecture.md).

---

## 1. Introduction

**Project title:** Mall Parking Flow — A Discrete-Event Simulation of Entry, Parking, and Exit Congestion.

**Background.** A mall parking lot is a queuing system. Vehicles arrive over time, wait at an
**entry gate**, search for and occupy a **parking slot**, dwell while their drivers shop, and
later queue at an **exit gate** to leave. Each gate lane can serve only one vehicle at a time,
and the lot has finite capacity, so congestion (queues) forms whenever demand outpaces service.

This project models that system with **discrete-event simulation (DES)** using Python + **SimPy**,
and visualizes it in a top-down browser dashboard so the behavior can be observed over time and
measured. The system is configured along **two independent axes**:

- **Scenario (demand profile)** — how busy the lot is and how fast gates serve: number of
  vehicles, arrival pattern, usable slots, and entry/exit service times.
- **Map (gate layout)** — the physical lot: how many entry gates and exit gates exist (1 or 2 of
  each). The map sets the gate *resource capacity*; the scenario sets the *load* on it.

Separating these axes lets us answer the classic operations question — *"one cashier vs. two
cashiers?"* — by running the **same demand** on a one-gate map and a two-gate map and comparing.

**Importance.** Parking congestion affects customer experience, safety, and mall throughput.
Simulation lets us test "what if" changes (more demand, fewer slots, slower gates, **an extra
gate lane**) **without rebuilding the real lot**, and quantify their impact on waiting time, queue
length, throughput, and resource utilization.

---

## 2. Problem Definition

**Problem.** Mall visitors experience delays at two bottlenecks: the **entry gate** (a queue
builds when arrivals cluster or the gate is slow) and the **exit gate** (a queue builds when many
vehicles leave at once or exit processing is slow). When the lot is full, vehicles are **denied**
entry entirely.

**Why it matters.** Long waits frustrate customers and can spill back onto public roads; denials
represent lost visits. Management needs to know *which* bottleneck dominates under different
conditions, how sensitive waiting time is to capacity and gate speed, and **whether adding a
second gate lane is worth it**.

**What the simulation analyzes.** For each operating condition (a scenario run on a chosen map),
the model measures average waiting time, queue lengths, throughput, gate utilization, and
processing time, and lets us compare conditions to identify the limiting resource and the effect
of adding gate capacity.

---

## 3. Objectives

1. **Analyze queue performance** at the entry and exit gates (waiting time and queue length).
2. **Measure resource utilization** of the entry gate(s), exit gate(s), and parking capacity.
3. **Quantify throughput** (vehicles completed per hour) and total time-in-system.
4. **Compare operational scenarios** — different arrival patterns, reduced capacity, slow entry
   service, and slow exit service — to identify and explain the dominant bottleneck in each.
5. **Compare gate configurations** — run the same demand on one-gate vs. two-gate maps to measure
   the benefit of adding an entry or exit lane ("one cashier vs. two cashiers").

---

## 4. System Model and Design

**Simulation type:** discrete-event, single replication per (scenario × map), deterministic
(seeded RNG).

| DES element | In this model |
| --- | --- |
| **Entities** | Vehicles (cars and motorcycles), each with an arrival time, a type, and — on multi-gate maps — an assigned entrance/exit lane. |
| **Events** | Arrival, join entry queue, entry-gate service start/end, gate crossing, slot search start/end (park), dwell end (exit request), exit-gate service start/end, gate crossing, departure (done). |
| **Resources** | Entry gate(s) (`simpy.Resource`, capacity = entry-gate count), exit gate(s) (one `simpy.Resource` per exit lane), and parking **slots** (typed pools: car slots and motorcycle slots). |
| **Queues** | Entry queue(s) (FIFO before each entry gate) and exit queue(s) (FIFO before each exit gate). |
| **State variables** | Per-vehicle state (11 states), number queued at each gate, slots occupied / free / targeted, denied count, completed count, simulation clock. |

**Two configuration axes.**

- **Scenario** selects a *demand profile* (vehicles, arrival pattern, usable slots, entry/exit
  service times). Five scenarios are provided (see §5).
- **Map** selects a *gate layout*. Four maps are provided, formed by crossing {1, 2} entry gates
  with {1, 2} exit gates: `one_entrance_one_exit`, `two_entrance_one_exit`,
  `one_entrance_two_exit`, `two_entrance_two_exit`. The map sets the SimPy resource capacity at
  each gate and the background image; a two-gate map splits arrivals/departures across two lanes.

**Vehicle lifecycle (state machine):** `scheduled → entry_queue → approaching_gate → gate_wait →
gate_crossing → searching → parked → exit_queue → exiting → done`, with a **denied** branch
(`gate_crossing → denied → exit_queue → … → done`) when no compatible slot is free. The full
flowchart is in [`flowchart.md`](flowchart.md); the conceptual architecture is in
[`architecture.md`](architecture.md).

**Behavior over time.** The server runs one full simulation per (scenario, map) and records a
timeline of frames (snapshots every 0.05 simulated minutes). The browser replays the frames, so
reviewers watch queues form and drain, slots fill, and gates open/close, while summary metrics are
computed from the per-vehicle event timestamps.

**Implementation:** `app/simulation.py` (model, paths, metrics), `app/api.py` (JSON API),
`app/static/` (dashboard). Source: this repository.

---

## 5. Assumptions and Input Data

**Assumptions**
- One deterministic, seeded run represents each scenario, so results are repeatable for review
  and testing (different seeds would give one sample of natural variation).
- Each gate lane serves one vehicle at a time (capacity 1 per lane); queue discipline is FIFO.
  A two-gate map = two parallel single-server lanes.
- Cars use car slots; motorcycles use motorcycle slots; a vehicle is **denied** if no compatible
  slot is free when it reaches the gate.
- On multi-gate maps, arriving/departing vehicles are split evenly (alternating) across the two
  lanes.
- Vehicles follow fixed, readable lanes (the model abstracts away free-form driving physics).
- Search time grows with occupancy (a fuller lot takes longer to find a space).

**Basis of input data (no field data available → justified assumptions).** Arrival times and
service/dwell times are generated from a seeded RNG within ranges chosen to produce realistic,
*observable* mall behavior. Each scenario changes only a few parameters from the baseline:

| Scenario | Vehicles | Usable slots | Arrival pattern | Entry service (min) | Exit service (min) |
| --- | --- | --- | --- | --- | --- |
| `baseline` | 44 | 72 | spread | 0.7 | 0.8 |
| `rush_hour` | 60 | 72 | clustered (early wave) | 1.0 | 0.95 |
| `limited_slots` | 60 | 16 (of 72 drawn) | spread, long dwell | 0.75 | 0.85 |
| `slow_entry` | 50 | 72 | spread | **3.2** | 0.8 |
| `exit_congestion` | 52 | 72 | spread | 0.7 | **4.0** |

Service time per vehicle = a base service value + a small random component; dwell (shopping) time
is drawn from a per-scenario range. Seeds: 101 / 202 / 303 / 404 / 505. The **map** axis is
orthogonal to this table — any scenario can run on any of the four gate layouts.

**Constraints and limitations.** Local class MVP (not deployed); single replication (no
confidence intervals); fixed lane geometry; per-lane gate capacity fixed at 1; no pricing/payment
modeling.

---

## 7. Experimental Results and Analysis

All runs are deterministic seeded results, produced by `app/simulation.py` and reproducible from
the dashboard's **"Compare scenarios"** view (which generates the table and bar charts live for a
chosen map).

### 7.1 Five scenarios on the base map (`one_entrance_one_exit`)

| Metric | baseline | rush_hour | limited_slots | slow_entry | exit_congestion |
| --- | --- | --- | --- | --- | --- |
| Avg **entry** wait (min) | 49.5 | 108.7 | 69.0 | **127.0** | 57.2 |
| Avg **exit** wait (min) | 33.7 | 37.6 | 45.0 | 5.5 | **119.0** |
| Avg time in system (min) | 131.5 | 195.4 | 182.8 | 183.5 | **228.8** |
| Entry **service** (min) | 1.75 | 2.09 | 1.81 | **4.27** | 1.75 |
| Exit **service** (min) | 0.98 | 1.10 | 1.02 | 0.94 | **4.19** |
| **Throughput** (veh/hr) | 9.7 | **10.0** | 7.5 | 8.4 | 6.5 |
| **Entry gate** utilization (%) | 58.0 | 65.7 | 58.4 | **86.0** | 39.3 |
| **Exit gate** utilization (%) | 80.2 | 85.1 | 79.9 | 69.3 | **89.3** |
| Avg entry queue | 8.0 | 18.1 | 11.0 | 17.8 | 6.2 |
| Avg exit queue | 5.4 | 6.3 | 7.2 | 0.8 | **13.0** |
| Max entry queue | 25 | **55** | 42 | 40 | 35 |
| Max exit queue | 13 | 15 | 18 | 4 | **29** |
| Denied vehicles | 0 | 0 | **13** | 0 | 0 |

**Interpretation**
- **baseline** — balanced: moderate waits, ~80% exit-gate utilization, no denials. Reference point.
- **rush_hour** — clustered arrivals more than double the entry wait (49→109 min) and push the
  entry queue to a peak of 55. The single gate still clears everyone, so throughput is highest
  (10/hr): the *demand pattern*, not capacity, is the stressor.
- **limited_slots** — cutting usable capacity from 72 to 16 causes **13 denials** and lowers
  throughput (7.5/hr); the binding constraint is **parking capacity**, not the gates.
- **slow_entry** — a slow entry gate drives **entry-gate utilization to 86%** and the highest
  entry wait (127 min), while the exit side stays idle (exit wait 5.5 min). Classic single-server
  bottleneck at the **entrance**.
- **exit_congestion** — a slow exit gate pushes **exit-gate utilization to 89%**, the largest exit
  queue (peak 29), and the longest time-in-system (229 min). The bottleneck is the **exit**.

**Scenario comparison (≥2 scenarios).** Contrasting **slow_entry vs. exit_congestion** isolates
the two bottlenecks at equal arrival load: the slow gate in each case becomes the high-utilization,
high-wait resource while the other gate is underused. Contrasting **baseline vs. rush_hour** shows
that the *same resources* produce very different queues purely from arrival clustering.

### 7.2 Gate-configuration comparison — "one cashier vs. two cashiers" (Map axis)

Here the **demand is held fixed** and only the **map** (gate count) changes. This is the direct
analogue of the rubric's "one cashier vs. two cashiers" example.

**slow_entry (entry is the bottleneck) — adding a second *entry* gate:**

| Map | Entry gates | Avg entry wait | Entry util % | Throughput (veh/hr) | Avg time in system |
| --- | --- | --- | --- | --- | --- |
| `one_entrance_one_exit` | 1 | **127.0** | 86.0 | 8.4 | 183.5 |
| `two_entrance_one_exit` | 2 | **52.1** | 51.0 | 10.0 | 151.3 |

➡ A second entry lane cuts the entry wait **~59% (127→52 min)**, drops entry-gate utilization from
86%→51% (the bottleneck is relieved), and raises throughput 8.4→10.0/hr. Adding an *exit* gate to
this scenario does almost nothing (`one_entrance_two_exit`: entry wait still 127) — confirming you
must add capacity **at the bottleneck**, not just anywhere.

**exit_congestion (exit is the bottleneck) — adding a second *exit* gate:**

| Map | Exit gates | Avg exit wait | Exit util % | Throughput (veh/hr) | Avg time in system |
| --- | --- | --- | --- | --- | --- |
| `one_entrance_one_exit` | 1 | **119.0** | 89.3 | 6.5 | 228.8 |
| `one_entrance_two_exit` | 2 | **18.2** | 77.9 | 11.4 | 127.2 |

➡ A second exit lane cuts the exit wait **~85% (119→18 min)**, nearly **doubles throughput
(6.5→11.4/hr)**, and almost halves time-in-system (229→127 min). Adding a second *entry* gate
instead (`two_entrance_one_exit`) makes exit congestion **worse** (exit wait 119→154 min): vehicles
get in faster only to pile up harder at the single exit — a textbook case of moving the bottleneck.

**rush_hour — full two-by-two map (two entry + two exit):**

| Map | Entry / Exit gates | Throughput (veh/hr) | Avg time in system | Max entry queue |
| --- | --- | --- | --- | --- |
| `one_entrance_one_exit` | 1 / 1 | 10.0 | 195.4 | 55 |
| `two_entrance_two_exit` | 2 / 2 | **17.3** | **118.7** | 50 |

➡ Doubling both gates lifts rush-hour throughput **+72% (10.0→17.3/hr)** and cuts time-in-system
by ~39%. (The peak entry queue barely moves because arrivals are clustered in a short burst — two
lanes drain the burst faster but it still forms.)

---

## 8. Conclusion and Recommendations

**Key findings**
- The system has two independent bottlenecks (entry and exit gates); which one dominates depends
  on the scenario, and **gate utilization** cleanly identifies it (the ~86–89% gate is the limiter).
- Arrival **clustering** (rush hour) inflates waiting time even when total capacity is adequate.
- **Parking capacity** is a separate constraint: when slots are scarce, vehicles are denied and
  throughput drops regardless of gate speed.
- **Adding a gate lane only helps at the bottleneck.** Quantitatively: a second entry gate cut the
  slow-entry wait 127→52 min; a second exit gate cut the exit-congestion wait 119→18 min and
  doubled throughput. Adding capacity at the *non*-bottleneck gate gave little or no benefit — and
  in exit_congestion a second *entry* gate made things worse by feeding the jammed exit faster.

**Recommendations**
- **Add a second lane at whichever gate is the bottleneck** for the expected pattern (a second
  entry gate for rush-hour entry surges; a second exit gate for end-of-day exit surges). Use gate
  utilization to decide which.
- **Stagger demand** (e.g., promotions outside peak) to flatten arrival clusters.
- Ensure usable capacity matches demand to avoid denials.

**Future work.** Multiple replications with confidence intervals, in-UI editing of arrival rates
and gate counts beyond the four preset maps, and CSV export of metrics for offline analysis.

---

*Reproducibility: results above are deterministic. Regenerate them with
`python3 -m uvicorn app.main:app` → dashboard "Compare scenarios", or run the model directly via
`app/simulation.py`. The behavior is covered by an automated test suite (`python3 -m unittest`,
**86 tests passing**).*
