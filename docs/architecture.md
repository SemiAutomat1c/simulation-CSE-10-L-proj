# Conceptual Model & Architecture

Two views for requirement item 4 (System Model and Design). Both render on GitHub / VS Code.

## Discrete-event conceptual model (entities · events · resources · queues · state)

```mermaid
flowchart LR
    subgraph ENT[Entities]
      V[Vehicles<br/>cars and motorcycles]
    end
    subgraph EV[Events]
      EA[arrival]
      ES[gate service start/end]
      ESR[search / park]
      EX[exit request]
      ED[departure]
    end
    subgraph RES[Resources]
      EG[(Entry gate<br/>capacity 1)]
      XG[(Exit gate<br/>capacity 1)]
      SL[(Parking slots<br/>car + motorcycle pools)]
    end
    subgraph Q[Queues - FIFO]
      EQ[Entry queue]
      XQ[Exit queue]
    end
    subgraph STATE[State variables]
      ST[vehicle state x10<br/>queue lengths<br/>slots free/occupied<br/>denied / completed<br/>sim clock]
    end

    V --> EA --> EQ --> EG --> ESR --> SL
    ESR --> EX --> XQ --> XG --> ED
    EG -.updates.-> ST
    XG -.updates.-> ST
    SL -.updates.-> ST
```

## Software architecture (how it runs)

```mermaid
flowchart TD
    B[Browser dashboard<br/>app/static: index.html, app.js, style.css]
    API[FastAPI app<br/>app/api.py]
    SIM[SimPy model<br/>app/simulation.py]

    B -- "GET /api/scenarios" --> API
    B -- "GET /api/simulation?scenario=" --> API
    B -- "GET /api/compare" --> API
    API -- run_simulation --> SIM
    SIM -- "frames + metrics (JSON)" --> API
    API -- JSON --> B
    B -- "replays timeline + renders metrics & comparison" --> U([Reviewer])
```

- **Backend** runs one deterministic SimPy simulation per scenario and returns a timeline of
  frames plus summary metrics.
- **`/api/compare`** returns metrics-only for all five scenarios (cached) for the comparison view.
- **Frontend** is dependency-free vanilla JS: it replays frames as an animation and renders the
  metrics, the comparison table, and the bar charts.
