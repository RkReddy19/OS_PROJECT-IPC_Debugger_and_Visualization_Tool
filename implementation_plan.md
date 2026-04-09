# IPC Debugger and Visualization Tool — Implementation Plan

Build a fully functional IPC Debugger desktop application in Python using Tkinter, multiprocessing, NetworkX, and Matplotlib. Users can create processes, define IPC connections, simulate communication, and visualize deadlocks/bottlenecks in real time.

## Proposed Changes

### Project Structure

```
OS PROJECT 2/
├── main.py                  # Entry point
├── event_logger.py          # Centralized event log
├── ipc_manager.py           # Pipe/Queue/SharedMemory wrappers
├── sync_manager.py          # Lock/Semaphore tracking wrappers
├── process_engine.py        # multiprocessing-based process spawner
├── deadlock_detector.py     # Wait-For Graph + DFS cycle detection
├── bottleneck_detector.py   # Queue depth & latency analysis
├── visualization.py         # NetworkX graph + Matplotlib rendering
├── gui.py                   # Tkinter GUI (3-panel layout)
└── IPC_Debugger_System_Design.md  # (existing report)
```

---

### Event Logger — `event_logger.py` [NEW]
- Thread-safe singleton logging class using `multiprocessing.Queue`
- Each event: `(timestamp, source_pid, dest_pid, action, data_size, details)`
- Methods: `log_event()`, `get_all_events()`, `clear()`
- Provides callback hook so GUI can receive new log entries in real time

---

### IPC Manager — `ipc_manager.py` [NEW]
- `IPCChannel` base class with `send()` / `receive()` + automatic event logging
- `PipeChannel` — wraps `multiprocessing.Pipe`
- `QueueChannel` — wraps `multiprocessing.Queue`, tracks queue depth
- `SharedMemoryChannel` — wraps `multiprocessing.Value`/`Array` with locks
- Factory function `create_channel(channel_type, ...)` to instantiate correct type

---

### Synchronization Manager — `sync_manager.py` [NEW]
- `TrackedLock` — wraps `multiprocessing.Lock`, records holder PID and waiters list
- `TrackedSemaphore` — wraps `multiprocessing.Semaphore` with counter tracking
- Exposes `get_lock_state()` → dict of `{lock_name: {holder, waiters[]}}` for deadlock analysis

---

### Process Simulation Engine — `process_engine.py` [NEW]
- `SimulatedProcess` class wrapping `multiprocessing.Process`
- Worker function receives: process config (ID, priority, behavior), IPC channels, sync primitives
- Behaviors: `producer` (sends messages), `consumer` (receives), `producer_consumer` (both)
- Supports pause/resume/stop via `multiprocessing.Event` flags
- Configurable delay to simulate priority differences

---

### Deadlock Detection — `deadlock_detector.py` [NEW]
- Builds a Wait-For Graph using `networkx.DiGraph`
- Nodes = process IDs, edges = "waiting-for" relationships from `sync_manager` state
- `detect_deadlock()` runs DFS-based cycle detection via `networkx.find_cycle()`
- Returns list of involved processes if cycle found, empty list otherwise

---

### Bottleneck Detection — `bottleneck_detector.py` [NEW]
- Analyzes event log for per-channel metrics: avg latency, throughput, queue depth over time
- Flags channels where queue depth exceeds threshold or latency ratio is high
- Returns ranked list of bottleneck channels with severity scores

---

### Visualization Engine — `visualization.py` [NEW]
- `IPCGraphVisualizer` class managing a `networkx.DiGraph`
- Nodes styled by state: green (running), yellow (waiting), red (deadlocked)
- Edges styled by channel type: solid (pipe), dashed (queue), dotted (shared memory)
- `update_graph()` method redraws onto a Matplotlib `FigureCanvasTkAgg`
- Separate `draw_metrics()` method for bar charts of latency/throughput

---

### GUI — `gui.py` [NEW]
Three-panel Tkinter layout:

**Left — Control Panel:**
- "Add Process" form: ID, priority slider, behavior dropdown
- "Add Connection" form: source, destination, channel type, message content
- Start / Pause / Stop / Reset buttons
- "Detect Deadlock" and "Analyze Bottlenecks" buttons

**Center — Visualization Canvas:**
- Embedded Matplotlib figure showing live NetworkX graph
- Animated edge highlights during message transfers
- Metrics chart below the graph

**Bottom — Log Panel:**
- Scrollable text widget showing timestamped events
- Color-coded by event type (send=green, receive=blue, deadlock=red, warning=orange)

---

### Main — `main.py` [NEW]
- Instantiates all modules, wires them together
- Launches Tkinter main loop
- Handles graceful shutdown of multiprocessing resources

---

## Verification Plan

### Automated (Launch Test)
Run `python main.py` from the project directory — the GUI window should render with all three panels visible and interactive.

### Manual Verification (User)
1. **Normal IPC flow:** Add 2 processes (Producer → Consumer) with a Queue connection. Click Start. Verify messages appear in the log and the graph shows green animated edges.
2. **Deadlock scenario:** Add 3 processes each holding one lock and waiting on another (circular). Click "Detect Deadlock". Verify the cycle is highlighted in red and an alert appears.
3. **Bottleneck scenario:** Add a fast producer and a slow consumer connected by a queue. Run simulation. Click "Analyze Bottlenecks". Verify the congested channel is flagged.
