# IPC Debugger — Implementation Plan

This document summarizes the implemented architecture for the IPC Debugger web app.

## Project Structure

```text
OS-PROJECT/
├── index.html
├── README.md
├── IMPLEMENTATION_PLAN.md
├── WALKTHROUGH.md
├── CONTRIBUTING.md
├── css/
│   └── styles.css
└── js/
    ├── app.js
    ├── process.js
    ├── pipe.js
    ├── messageQueue.js
    ├── sharedMemory.js
    ├── semaphore.js
    ├── debugger.js
    ├── visualizer.js
    ├── timeline.js
    └── logger.js
```

## Modules

- `js/app.js`: Simulation orchestration, scenarios, controls, and UI updates.
- `js/process.js`: Process model and state transitions.
- `js/pipe.js`: Pipe-based IPC simulation.
- `js/messageQueue.js`: FIFO message queue IPC simulation.
- `js/sharedMemory.js`: Shared-memory read/write simulation.
- `js/semaphore.js`: Semaphore synchronization behavior.
- `js/debugger.js`: Deadlock, race condition, and bottleneck checks.
- `js/visualizer.js`: SVG rendering for processes and IPC edges.
- `js/timeline.js`: Timeline/state history rendering.
- `js/logger.js`: Event logging and report export.

## Verification Checklist

1. Open `index.html` in a browser.
2. Select each scenario and verify expected behavior.
3. Test Play/Pause/Step/Reset controls.
4. Confirm alerts, log updates, and timeline updates.
5. Export report and verify file output.
