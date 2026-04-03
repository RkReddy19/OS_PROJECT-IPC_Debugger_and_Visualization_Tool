# IPC Debugger — Inter-Process Communication Visualizer

A web-based interactive tool for visualizing and debugging Inter-Process Communication (IPC) mechanisms. This project demonstrates processes, pipes, message queues, shared memory, and semaphores with real-time visualization and automated debugging detection.

## Features

- **Process Simulator** — Simulate processes with multiple states (ready, running, waiting, blocked, terminated)
- **4 IPC Mechanisms**:
  - Pipes (unidirectional communication)
  - Message Queues (FIFO message passing)
  - Shared Memory (concurrent access)
  - Semaphores (synchronization primitives)
- **Debugging Engine**:
  - Deadlock detection using cycle detection
  - Race condition detection
  - Bottleneck analysis
- **6 Pre-built Scenarios** — Pipe Communication, Message Queue, Deadlock, Race Condition, Bottleneck, Complex Multi-IPC
- **Real-time Visualization** — Animated process graph with data flow particles
- **Timeline View** — Color-coded process state history
- **Event Log** — Timestamped log of all IPC operations
- **Export Report** — Download debug analysis as a report

## Getting Started

### Prerequisites

- Any modern web browser (Chrome, Firefox, Edge, Safari)
- No build tools or server required — runs directly in the browser

### How to Use

1. **Open the project**
   - Open `index.html` directly in your web browser
   - You can double-click the file or drag it to your browser window

2. **Select a scenario**
   - Use the dropdown in the **Control Panel** (left sidebar)
   - Choose from: Pipe Communication, Message Queue, Deadlock, Race Condition, Bottleneck, or Complex Multi-IPC

3. **Control the simulation**
   - **▶ Play** — Run simulation continuously
   - **⏸ Pause** — Pause the simulation
   - **⏭ Step** — Advance exactly one simulation tick (best for detailed observation)
   - **⏹ Reset** — Stop and reset to initial state

4. **Adjust speed**
   - Use the **Speed slider** (1x to 10x) to control simulation speed during playback

5. **Monitor the simulation**
   - **Process Nodes** — Colored circles representing processes
     - Green = Ready/Running
     - Yellow = Waiting
     - Red = Blocked
     - Gray = Terminated
   - **Connections** — Lines between processes showing IPC channels
   - **Data Flow** — Animated particles flowing along connections
   - **Debug Alerts** — Red warnings for deadlocks, race conditions, bottlenecks

6. **View details**
   - **Event Log** — Bottom panel shows timestamped log of all IPC events
   - **Timeline View** — Visual history of process states over time
   - **Metrics Panel** — Statistics about processes and IPC operations

7. **Export results**
   - Click **📄 Export Report** to download a debug summary as a text file

## Project Structure

```
OS-PROJECT-main/
├── index.html              # Main dashboard (entry point)
├── README.md              # This file
├── Implementation Plan    # Project specification
├── Walkthrough            # Feature walkthrough
├── css/
│   └── styles.css         # Dark-mode design system and all styles
└── js/
    ├── app.js             # Main app controller and scenario management
    ├── process.js         # Process simulator and state management
    ├── pipe.js            # Pipe IPC mechanism
    ├── messageQueue.js    # Message Queue IPC mechanism
    ├── sharedMemory.js    # Shared Memory IPC mechanism
    ├── semaphore.js       # Semaphore synchronization primitive
    ├── debugger.js        # Deadlock, race condition, bottleneck detection
    ├── visualizer.js      # SVG-based process graph rendering
    ├── timeline.js        # Timeline view for process state history
    └── logger.js          # Event logging and report export
```

## Scenarios Explained

### 1. Pipe Communication
Two processes communicate through a unidirectional pipe. Demonstrates basic IPC through buffered data flow.

### 2. Message Queue
Processes exchange messages through a FIFO queue. Shows message-based communication.

### 3. Deadlock Scenario
Two processes become deadlocked waiting for resources held by each other. The debugger detects this circular wait.

### 4. Race Condition
Multiple processes access and modify shared memory simultaneously without proper synchronization, causing conflicting writes.

### 5. Bottleneck
A single shared resource receives requests from many processes, creating a performance bottleneck.

### 6. Complex Multi-IPC
Multiple processes using pipes, queues, and shared memory simultaneously in a complex scenario.

## Debugging Features

### Deadlock Detection
- Analyzes the wait-for graph for circular dependencies
- When detected: processes turn red and alert shows "Circular wait: P1 → P2 → P1"

### Race Condition Detection
- Monitors concurrent access to shared memory
- Flags when two processes write to the same memory location simultaneously
- Alert displays conflicting accesses

### Bottleneck Analysis
- Identifies resources receiving disproportionate requests
- Shows which process is the bottleneck and impact on others

## Tips for Best Results

- **Use Step Mode (⏭)** for detailed observation of individual events
- **Watch the Timeline** to see how process states evolve over time
- **Check the Event Log** for precise timing of each operation
- **Try different scenarios** to understand different IPC patterns and problems
- **Slow down the speed** if animations are too fast

## Browser Compatibility

- Chrome/Chromium: Full support
- Firefox: Full support
- Edge: Full support
- Safari: Full support

## Technical Details

- **Built with** vanilla HTML, CSS, and JavaScript (no frameworks)
- **Rendering**: SVG for process visualization and animations
- **Architecture**: Modular design with separate concerns (processes, IPC, debugging, visualization)
- **No dependencies**: Runs entirely client-side

## File Descriptions

| File | Purpose |
|------|---------|
| `index.html` | Main HTML dashboard with UI layout |
| `css/styles.css` | Complete design system with animations and themes |
| `js/app.js` | Application controller, scenario presets, and simulation loop |
| `js/process.js` | Process creation, state management, and lifecycle |
| `js/pipe.js` | Pipe IPC implementation with buffer management |
| `js/messageQueue.js` | FIFO message queue implementation |
| `js/sharedMemory.js` | Shared memory with concurrent access tracking |
| `js/semaphore.js` | Semaphore primitive with wait/signal operations |
| `js/debugger.js` | Deadlock, race condition, and bottleneck detection |
| `js/visualizer.js` | SVG rendering of process graph and animations |
| `js/timeline.js` | Timeline visualization of process states |
| `js/logger.js` | Event logging system and report export |

## Keyboard Shortcuts (Future Enhancement)

Currently not implemented, but the UI is ready for:
- `Space` to play/pause
- `Right Arrow` to step
- `Ctrl+R` to reset
- `Ctrl+E` to export

## Performance Notes

- Smooth animation support up to 50+ concurrent processes
- Simulation runs at ~60 FPS when playing
- Step mode allows detailed inspection without performance concerns

## License

Educational project for Operating Systems course.

## Notes

- This project is designed to run immediately without any build process
- All code is vanilla JavaScript for portability and ease of presentation
- The simulator is deterministic — same scenario always produces the same sequence of events (useful for reproducible testing)
