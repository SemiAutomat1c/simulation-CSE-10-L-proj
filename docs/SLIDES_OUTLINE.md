# Presentation Slides — Outline

Target: 15–20 min presentation + demo, then 5–10 min Q&A. Map each slide to the rubric item.
Pull figures from [`REPORT.md`](REPORT.md), diagrams from [`flowchart.md`](flowchart.md) and
[`architecture.md`](architecture.md), and do the live demo from the running dashboard.

1. **Title** — project title, course/section, group members, instructor, date.
2. **Introduction (item 1)** — what a mall lot is as a queuing system; why congestion matters.
3. **Problem Definition (item 2)** — two bottlenecks (entry gate, exit gate) + denials when full.
4. **Objectives (item 3)** — analyze queue performance, measure utilization, quantify throughput,
   compare scenarios.
5. **System Model (item 4a)** — entities / events / resources / queues / state variables table;
   show the **conceptual diagram** (architecture.md).
6. **Process Flow (item 4b)** — the **vehicle lifecycle flowchart** (flowchart.md); name the 10 states.
7. **Assumptions & Input Data (item 5)** — seeded RNG, FIFO gates, car vs. moto slots, the
   per-scenario parameter table.
8. **LIVE DEMO (item 6)** — run `baseline`, point out entry queue → gate → search → park → exit;
   switch to `rush_hour`, then `limited_slots` (show denials). Use the speed slider / replay.
   *Be ready to switch scenarios on request (covers "modify inputs during questioning").*
9. **Results — metrics (item 7a)** — open the **Performance** panel; define avg waiting time,
   throughput, gate utilization, processing time, time-in-system.
10. **Results — comparison (item 7b)** — open **"Compare scenarios"**: walk the table + bar charts;
    contrast **slow_entry vs. exit_congestion** (which gate is the bottleneck) and
    **baseline vs. rush_hour** (same capacity, arrival clustering).
11. **Conclusion & Recommendations (item 8)** — utilization identifies the bottleneck; add a second
    lane at the limiting gate; stagger demand; match capacity to demand.
12. **Q&A / Thank you** — repo link; note tests (`python3 -m unittest`, 61 passing).

**Demo cheat-sheet (headline numbers):** slow_entry → entry wait **127 min**, entry-gate util **86%**;
exit_congestion → exit wait **119 min**, exit-gate util **89%**, max exit queue **29**;
rush_hour → max entry queue **55**, throughput **10/hr**; limited_slots → **13 denied**.
