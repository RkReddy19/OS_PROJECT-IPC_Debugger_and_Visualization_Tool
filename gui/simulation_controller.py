"""
Simulation Controller — extracted from app.py to reduce God-class size.
Handles all simulation lifecycle callbacks: start, pause, resume, stop,
reset, and analysis operations (deadlock, bottleneck, race detection).
"""

import threading
import tkinter as tk
from tkinter import messagebox
from typing import TYPE_CHECKING, Dict, List, Optional

from utils.constants import COLORS
from utils.event_logger import EventLogger
from engine.process_engine import ProcessEngine
from engine.sync_manager import SynchronizationManager
from analyzers.deadlock_detector import DeadlockDetector
from analyzers.bottleneck_detector import BottleneckDetector
from analyzers.race_detector import RaceConditionDetector

if TYPE_CHECKING:
    from gui.animated_canvas import AnimatedCanvas
    from gui.metrics_panel import MetricsPanel
    from gui.log_panel import LogPanel

C = COLORS


class SimulationController:
    """Owns all simulation and analysis callbacks, delegated from the GUI."""

    def __init__(
        self,
        root: tk.Tk,
        engine: ProcessEngine,
        sync_manager: SynchronizationManager,
        logger: EventLogger,
        deadlock_detector: DeadlockDetector,
        bottleneck_detector: BottleneckDetector,
        race_detector: RaceConditionDetector,
    ) -> None:
        self.root = root
        self.engine = engine
        self.sync_manager = sync_manager
        self.logger = logger
        self.deadlock_detector = deadlock_detector
        self.bottleneck_detector = bottleneck_detector
        self.race_detector = race_detector

        # GUI references — set by app.py after construction
        self.animated_canvas: Optional["AnimatedCanvas"] = None
        self.metrics_panel: Optional["MetricsPanel"] = None
        self.log_panel: Optional["LogPanel"] = None
        self.status_label: Optional[tk.Label] = None
        self.pause_btn: Optional[tk.Button] = None
        self.auto_deadlock_var: Optional[tk.BooleanVar] = None

        # Data references — set by app.py
        self.channels: list = []
        self.connections: list = []
        self.process_configs: dict = {}

        # Threshold entry references — set by app.py
        self.entry_thresh_depth: Optional[tk.Entry] = None
        self.entry_thresh_latency: Optional[tk.Entry] = None
        self.entry_thresh_ratio: Optional[tk.Entry] = None

        # State
        self.simulation_running = False
        self._refresh_timer: Optional[str] = None

        # Speed control (1.0 = normal)
        self.speed_var: Optional[tk.DoubleVar] = None

        # Callbacks for UI refresh — set by app.py
        self._refresh_canvas_fn = None
        self._refresh_process_cards_fn = None
        self._refresh_connection_cards_fn = None
        self._update_pid_lists_fn = None

    # ════════════════════════════════════════════
    # SIMULATION LIFECYCLE
    # ════════════════════════════════════════════

    def start_simulation(self) -> None:
        """Start the simulation."""
        if not self.process_configs:
            messagebox.showwarning("Simulation", "Add at least one process first.")
            return
        self.simulation_running = True
        self._apply_speed()
        self.status_label.config(text="  Running  ", fg=C["accent_ok"], bg="#16a34a")
        self.logger.log_event(source_pid="SYSTEM", dest_pid="", action="INFO",
                              details="Simulation started")
        self.engine.start_all()
        self._start_refresh_timer()

    def pause_simulation(self) -> None:
        """Pause the simulation and toggle button to Resume."""
        self.engine.pause_all()
        self.status_label.config(text="  Paused  ", fg="#fff", bg=C["accent_warn"])
        self.logger.log_event(source_pid="SYSTEM", dest_pid="", action="INFO",
                              details="Simulation paused")
        # Toggle button to Resume
        if self.pause_btn:
            self.pause_btn.config(text="Resume",
                                  command=self.resume_simulation)
        self._do_ui_refresh()

    def resume_simulation(self) -> None:
        """Resume the simulation and toggle button back to Pause."""
        self.engine.resume_all()
        self.status_label.config(text="  Running  ", fg="#fff", bg="#16a34a")
        self.logger.log_event(source_pid="SYSTEM", dest_pid="", action="INFO",
                              details="Simulation resumed")
        # Toggle button back to Pause
        if self.pause_btn:
            self.pause_btn.config(text="Pause",
                                  command=self.pause_simulation)
        self._do_ui_refresh()

    def stop_simulation(self) -> None:
        """Stop the simulation."""
        self.simulation_running = False
        self.engine.stop_all()
        self._stop_refresh_timer()
        self.status_label.config(text="  Stopped  ", fg="#94a3b8", bg="#1e293b")
        # Reset pause button back to Pause state
        if self.pause_btn:
            self.pause_btn.config(text="Pause",
                                  command=self.pause_simulation)
        self.logger.log_event(source_pid="SYSTEM", dest_pid="", action="INFO",
                              details="Simulation stopped")
        self._do_ui_refresh()

    def reset_all(self, force: bool = False) -> None:
        """Stop everything, clear all data, and reset the UI.

        Args:
            force: If True, skip the confirmation dialog (used by scenario loaders).
        """
        if not force and (self.process_configs or self.channels):
            if not messagebox.askyesno(
                "Confirm Reset",
                "This will remove all processes and connections. Continue?"
            ):
                return
        self._reset_impl()

    def _reset_impl(self) -> None:
        """Internal reset — no confirmation dialog."""
        self.stop_simulation()
        for ch in self.channels:
            ch.close()
        self.channels.clear()
        self.connections.clear()
        self.process_configs.clear()
        self.engine.reset()
        self.sync_manager.reset()
        self.deadlock_detector.reset()
        self.race_detector.reset()
        if self.animated_canvas:
            self.animated_canvas.clear_deadlock_info()
        self.logger.reset()
        if self._update_pid_lists_fn:
            self._update_pid_lists_fn()
        if self.log_panel:
            self.log_panel.clear()
        if self.metrics_panel:
            self.metrics_panel.hide()
        self.status_label.config(text="\u25cb  Idle", fg=C["text_muted"])
        self._do_ui_refresh()

    # ════════════════════════════════════════════
    # ANALYSIS
    # ════════════════════════════════════════════

    def detect_deadlock(self) -> None:
        """Run deadlock detection."""
        pids = list(self.process_configs.keys())
        if not pids:
            messagebox.showinfo("Deadlock", "No processes to analyze.")
            return
        cycle_edges = self.deadlock_detector.detect_deadlock(pids)
        if cycle_edges:
            involved = self.deadlock_detector.get_involved_processes()
            if self.animated_canvas:
                self.animated_canvas.set_deadlock_info(involved, cycle_edges)
            for pid in involved:
                p = self.engine.get_process(pid)
                if p:
                    p.mark_deadlocked()
            n = len(self.deadlock_detector.last_cycles)
            messagebox.showerror("\U0001f534 Deadlock!",
                f"{n} cycle(s) found!\nInvolved: {', '.join(involved)}")
        else:
            if self.animated_canvas:
                self.animated_canvas.clear_deadlock_info()
            messagebox.showinfo("Deadlock", "\u2705 No deadlock detected.")
        self._do_ui_refresh()

    def analyze_bottlenecks(self) -> None:
        """Run bottleneck analysis."""
        if not self.channels:
            messagebox.showinfo("Bottleneck", "No channels to analyze.")
            return
        try:
            self.bottleneck_detector.queue_depth_threshold = int(
                self.entry_thresh_depth.get())
        except ValueError:
            pass
        try:
            self.bottleneck_detector.latency_threshold = float(
                self.entry_thresh_latency.get())
        except ValueError:
            pass
        try:
            self.bottleneck_detector.throughput_ratio_threshold = float(
                self.entry_thresh_ratio.get())
        except ValueError:
            pass
        reports = self.bottleneck_detector.analyze_channels(self.channels)
        if reports:
            msg = "\n".join(
                f"\u2022 [{r.severity}] {r.channel_name}: {r.details}"
                for r in reports)
            messagebox.showwarning("\U0001f4ca Bottlenecks", msg)
        else:
            messagebox.showinfo("Bottleneck", "\u2705 No bottlenecks detected.")

    def detect_races(self) -> None:
        """Run race condition detection."""
        reports = self.race_detector.detect_races()
        if reports:
            msg = "\n".join(f"\u2022 {r.details}" for r in reports)
            messagebox.showwarning("\u26a1 Race Conditions", msg)
        else:
            messagebox.showinfo("Races", "\u2705 No race conditions detected.")

    def show_metrics(self) -> None:
        """Show performance metrics charts."""
        if not self.channels:
            messagebox.showinfo("Metrics", "No channels yet.")
            return
        metrics = self.bottleneck_detector.get_channel_metrics(self.channels)
        self.metrics_panel.update_metrics(metrics, channels=self.channels)
        self.metrics_panel.show()

    # ════════════════════════════════════════════
    # REFRESH TIMER
    # ════════════════════════════════════════════

    def _start_refresh_timer(self) -> None:
        self._stop_refresh_timer()

        def tick():
            if self.simulation_running:
                self._do_ui_refresh()
                if self.auto_deadlock_var and self.auto_deadlock_var.get():
                    self._auto_detect_worker()
                self._refresh_timer = self.root.after(2000, tick)
        self._refresh_timer = self.root.after(2000, tick)

    def _stop_refresh_timer(self) -> None:
        if self._refresh_timer:
            self.root.after_cancel(self._refresh_timer)
            self._refresh_timer = None

    def _auto_detect_worker(self) -> None:
        """Run deadlock detection in a background thread to avoid blocking UI."""
        pids = list(self.process_configs.keys())
        if not pids:
            return

        def worker():
            edges = self.deadlock_detector.detect_deadlock(pids)
            self.root.after(0, lambda: self._handle_auto_deadlock(edges))

        threading.Thread(target=worker, daemon=True).start()

    def _handle_auto_deadlock(self, edges) -> None:
        """Handle auto-deadlock result on the main thread."""
        if edges and self.animated_canvas:
            involved = self.deadlock_detector.get_involved_processes()
            self.animated_canvas.set_deadlock_info(involved, edges)
            for pid in involved:
                p = self.engine.get_process(pid)
                if p:
                    p.mark_deadlocked()

    def _do_ui_refresh(self) -> None:
        """Refresh all UI components."""
        if self._refresh_canvas_fn:
            self._refresh_canvas_fn()
        if self._refresh_process_cards_fn:
            self._refresh_process_cards_fn()

    # ════════════════════════════════════════════
    # SPEED CONTROL
    # ════════════════════════════════════════════

    def _apply_speed(self) -> None:
        """Apply speed multiplier to all process delays."""
        if not self.speed_var:
            return
        speed = self.speed_var.get()
        if speed <= 0:
            speed = 1.0
        # Speed > 1 means faster (shorter delays)
        for pid, cfg in self.process_configs.items():
            # Store original delay if not already stored
            if not hasattr(cfg, '_original_delay'):
                cfg._original_delay = cfg.delay
            cfg.delay = cfg._original_delay / speed

    def step_simulation(self) -> None:
        """Run one cycle of the simulation, then pause."""
        if not self.process_configs:
            messagebox.showwarning("Simulation", "Add at least one process first.")
            return
        if not self.simulation_running:
            # Start and immediately schedule a pause
            self.start_simulation()
        # Schedule pause after a short delay (one cycle)
        self.root.after(200, self.pause_simulation)
        self.logger.log_event(source_pid="SYSTEM", dest_pid="", action="INFO",
                              details="Step: one cycle executed")
