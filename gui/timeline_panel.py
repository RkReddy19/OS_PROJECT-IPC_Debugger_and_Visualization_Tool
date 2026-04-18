"""
Timeline Panel — Matplotlib Gantt-style process lifecycle visualization.
Shows process states over time with event markers.
"""

import tkinter as tk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from typing import List, Dict, Optional
import matplotlib.patches as mpatches

from utils.models import LogEvent
from utils.constants import COLORS


STATE_COLORS_MPL = {
    "running":    "#22c55e",
    "idle":       "#94a3b8",
    "paused":     "#f59e0b",
    "stopped":    "#64748b",
    "deadlocked": "#ef4444",
}

EVENT_MARKERS = {
    "SEND":         ("^", "#22c55e", 5),   # triangle up
    "RECEIVE":      ("v", "#38bdf8", 5),   # triangle down
    "LOCK_ACQUIRE": ("s", "#fb923c", 4),   # square
    "LOCK_RELEASE": ("o", "#94a3b8", 4),   # circle
    "DEADLOCK":     ("X", "#ef4444", 7),   # X marker
}


class TimelinePanel:
    """Gantt-style process timeline with event markers."""

    def __init__(self, parent: tk.Widget):
        self.parent = parent
        self.fig = Figure(figsize=(8, 3), dpi=100, facecolor=COLORS["bg"])
        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.widget = self.canvas.get_tk_widget()
        self._visible = False

    def show(self):
        if not self._visible:
            self.widget.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
            self._visible = True

    def hide(self):
        if self._visible:
            self.widget.pack_forget()
            self._visible = False

    def update_timeline(self, events: List[LogEvent],
                        process_ids: List[str]) -> None:
        """Render the timeline from event data."""
        self.fig.clear()
        self.fig.patch.set_facecolor(COLORS["bg"])

        if not events or not process_ids:
            ax = self.fig.add_subplot(111)
            ax.set_facecolor(COLORS["bg"])
            ax.text(0.5, 0.5, "No timeline data.\nRun a simulation first.",
                    ha='center', va='center', fontsize=12,
                    color=COLORS["text_muted"], transform=ax.transAxes)
            ax.axis('off')
            self.canvas.draw()
            return

        ax = self.fig.add_subplot(111)
        ax.set_facecolor(COLORS["panel_bg"])

        pid_indices = {pid: i for i, pid in enumerate(process_ids)}
        num_pids = len(process_ids)

        # Build state intervals per process
        # Track state transitions from INFO events
        state_intervals: Dict[str, List] = {pid: [] for pid in process_ids}
        current_states: Dict[str, tuple] = {}  # pid -> (state, start_time)

        for event in events:
            pid = event.source_pid
            if pid not in pid_indices:
                continue

            if event.action == "INFO":
                details_lower = event.details.lower()
                if "started" in details_lower:
                    new_state = "running"
                elif "paused" in details_lower:
                    new_state = "paused"
                elif "resumed" in details_lower:
                    new_state = "running"
                elif "stopped" in details_lower:
                    new_state = "stopped"
                else:
                    continue

                # Close previous state interval
                if pid in current_states:
                    prev_state, start_t = current_states[pid]
                    state_intervals[pid].append(
                        (start_t, event.timestamp, prev_state))

                current_states[pid] = (new_state, event.timestamp)

        # Close any open intervals
        max_time = max(e.timestamp for e in events) if events else 1.0
        for pid, (state, start_t) in current_states.items():
            state_intervals[pid].append((start_t, max_time, state))

        # Draw state bars
        bar_height = 0.6
        for pid, intervals in state_intervals.items():
            y = pid_indices[pid]
            for start, end, state in intervals:
                width = max(end - start, 0.01)
                color = STATE_COLORS_MPL.get(state, "#94a3b8")
                ax.barh(y, width, left=start, height=bar_height,
                        color=color, alpha=0.75, edgecolor="none")

        # Draw event markers
        for event in events:
            pid = event.source_pid
            if pid not in pid_indices:
                continue
            if event.action in EVENT_MARKERS:
                marker, color, size = EVENT_MARKERS[event.action]
                y = pid_indices[pid]
                ax.plot(event.timestamp, y, marker=marker,
                        color=color, markersize=size, alpha=0.9,
                        markeredgecolor="white", markeredgewidth=0.5)

        # Formatting
        ax.set_yticks(range(num_pids))
        ax.set_yticklabels(process_ids, fontsize=9, color=COLORS["text"])
        ax.set_xlabel("Time (s)", fontsize=9, color=COLORS["text_muted"])
        ax.set_title("Process Timeline", fontsize=11, color=COLORS["accent"],
                     fontweight="bold")
        ax.tick_params(colors=COLORS["text_dim"], labelsize=8)
        for spine in ax.spines.values():
            spine.set_color(COLORS["text_dim"])
        ax.set_xlim(0, max_time * 1.05)
        ax.set_ylim(-0.5, num_pids - 0.5)
        ax.invert_yaxis()

        # Legend
        legend_patches = [
            mpatches.Patch(color=c, label=s.capitalize())
            for s, c in STATE_COLORS_MPL.items()
            if s in ("running", "paused", "stopped", "deadlocked")
        ]
        ax.legend(handles=legend_patches, loc="upper right",
                  fontsize=7, facecolor=COLORS["panel_bg"],
                  edgecolor=COLORS["text_dim"], labelcolor=COLORS["text"])

        self.fig.tight_layout()
        self.canvas.draw()
