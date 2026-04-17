# IPC Debugger — Walkthrough

## What Was Built

A browser-based IPC debugger and visualizer with:

- Process simulation (ready/running/waiting/blocked/terminated)
- IPC mechanisms: Pipes, Message Queues, Shared Memory, and Semaphores
- Debug analysis: deadlock, race condition, and bottleneck detection
- Scenario-driven simulation controls
- Real-time SVG visualization, event log, timeline, and report export

## Key Files

- `index.html` — Main dashboard layout
- `css/styles.css` — UI styling and animations
- `js/app.js` — Main controller and simulation loop
- `js/*.js` — IPC, process, visualization, logging, and debugging modules

## Usage

1. Open `index.html` in a modern browser.
2. Select a scenario from the control panel.
3. Use Play/Pause/Step/Reset controls.
4. Observe visualization, alerts, event log, and timeline.
5. Export a report using the export button.

## Notes

- This walkthrough intentionally uses only repository-relative paths.
- Local-machine file links and local screenshot paths were removed for portability.
