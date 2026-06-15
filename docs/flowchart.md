# Vehicle Lifecycle Flowchart (Process Diagram)

This is the per-vehicle process the simulation runs (requirement item 4). It renders on
GitHub and in VS Code's Markdown preview — screenshot it for the slides.

```mermaid
flowchart TD
    A([Arrival: vehicle scheduled]) --> B[Join ENTRY QUEUE]
    B --> C{Entry gate free?}
    C -- no --> B
    C -- yes --> D[Approach gate]
    D --> E[Gate wait + entry service]
    E --> F[Reserve a slot]
    F --> G{Compatible slot free?}
    G -- no --> DEN[DENIED]
    G -- yes --> H[Cross gate into lot]
    H --> I[SEARCH for slot]
    I --> J[PARKED - dwell while shopping]
    J --> K[Exit requested - release slot]
    DEN --> L[Join EXIT QUEUE]
    K --> L
    L --> M{Exit gate free?}
    M -- no --> L
    M -- yes --> N[Exit service at gate]
    N --> O[Merge to outside road]
    O --> P([DONE - departed])

    classDef queue fill:#2b3a4a,stroke:#4e9cff,color:#fff;
    classDef gate fill:#3a2b2b,stroke:#ef5b54,color:#fff;
    classDef done fill:#22402b,stroke:#55d47f,color:#fff;
    class B,L queue;
    class E,N gate;
    class P done;
```

**Mapping to the 10 vehicle states:** `scheduled` (A) → `entry_queue` (B) →
`approaching_gate` (D) → `gate_wait` (E) → `gate_crossing` (H) → `searching` (I) →
`parked` (J) → `exit_queue` (L) → `exiting` (N/O) → `done` (P), with the `denied` branch (DEN).

**Resources held:** the **entry gate** is held from D through H; the **exit gate** from N through O;
a **parking slot** from F (reserve) until K (release).
