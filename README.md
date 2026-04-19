# IPC Debugger & Visualization Tool

A desktop application for simulating Inter-Process Communication (IPC), visualizing process interactions in real time, and detecting common concurrency issues such as deadlocks, bottlenecks, and race conditions.

This project is designed to be both practical and educational: you can build custom topologies from scratch, or run predefined scenarios to observe classic synchronization problems.

## What This Project Does

- Simulates concurrent process behavior with configurable roles and delays
- Supports multiple IPC channel types:
	- Pipe
	- Queue
	- Shared Memory
- Visualizes process topology and message flow on an animated canvas
- Detects:
	- Deadlocks (Wait-For Graph cycle analysis)
	- Bottlenecks (depth/latency/throughput analysis)
	- Race conditions (time-window access conflict detection)
- Provides timeline and message-browser views for debugging history
- Exports reports and logs (HTML, CSV, PNG, text metrics)

## Core Modules

- `gui/`: UI, animated canvas, scenario loading, dashboard controls
- `engine/`: process simulation runtime and synchronization primitives
- `ipc/`: channel abstractions and concrete channel implementations
- `analyzers/`: deadlock, bottleneck, race, and report generation logic
- `utils/`: shared models, constants, event logging/emitter utilities
- `tests/`: unit and smoke tests for channels, analyzers, models, engine, and scenarios

## Requirements

- Windows (recommended), macOS, or Linux
- Python 3.10+
- Tkinter (usually included with standard Python builds)

Python packages used by the project include:

- `matplotlib`
- `networkx`
- `pytest` (for test execution)

## Setup

1. Clone the repository.
2. Open a terminal in the project root.
3. (Recommended) Create and activate a virtual environment.
4. Install dependencies:

```bash
py -m pip install matplotlib networkx pytest
```

If you use `python` instead of `py`, replace commands accordingly.

## Run the Application

Launch the main GUI:

```bash
py main.py
```

Open the landing page in your browser:

```bash
py launch_landing.py
```

Run integrated scenario checks (headless logic flow):

```bash
py run_all_scenarios.py
```

## Typical Workflow

1. Add processes in the **Processes** tab.
2. Connect them through IPC channels in the **Connections** tab.
3. Start simulation and monitor the animated topology.
4. Use **Analyze** tools for deadlock/bottleneck/race detection.
5. Inspect timeline and message history.
6. Export artifacts from the **Export** tab.

## Built-In Scenarios

- **Normal IPC**: basic producer-consumer flow
- **Deadlock**: circular lock dependency across processes
- **Bottleneck**: fast producer and slow consumer queue pressure
- **Race Condition**: concurrent writes to shared memory
- **Pipeline**: multi-stage mixed-IPC chain

## Keyboard Shortcuts

- `Ctrl+S`: Start simulation
- `Ctrl+P`: Pause simulation
- `Ctrl+R`: Reset all
- `Ctrl+D`: Run deadlock detection
- `Ctrl+B`: Run bottleneck analysis

## Testing

Run the full test suite:

```bash
py -m pytest
```

Run GUI smoke tests with skip reasons shown (useful in headless environments):

```bash
py -m pytest -rs tests/test_gui_smoke.py
```

## Project Structure

```text
.
├── analyzers/
├── engine/
├── gui/
├── ipc/
├── landing/
├── tests/
├── utils/
├── main.py
├── launch_landing.py
└── run_all_scenarios.py
```

## Troubleshooting

### 1) `python` command not found on Windows

Use the launcher form:

```bash
py main.py
```

### 2) GUI tests are skipped

This is expected in headless/no-display environments.

### 3) Tkinter errors at startup

Ensure your Python build includes Tk support and your display environment is available.

### 4) Export or plotting issues

Confirm `matplotlib` is installed and writable output paths are used.

## Additional Documentation

- `IPC_Debugger_System_Design.md`
- `IPC_Debugger_Project_Analysis_Report.md`
- `REPORT/IPC_Debugger_Interface_Report.md`

