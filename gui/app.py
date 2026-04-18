"""
Main GUI Application — Modern tab-based dashboard with card UI.
Complete redesign with dark theme, emoji icons, and clean layout.

Delegates simulation lifecycle to SimulationController (Fix #20).
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, Dict, List

import matplotlib
matplotlib.use('TkAgg')

from utils.models import LogEvent, ProcessConfig
from utils.event_logger import EventLogger
from utils.constants import (
    COLORS, BEHAVIOR_ICONS, STATE_ICONS, REFRESH_INTERVAL_MS,
)
from ipc import create_channel, IPCChannel
from engine.sync_manager import SynchronizationManager
from engine.process_engine import ProcessEngine
from analyzers.deadlock_detector import DeadlockDetector
from analyzers.bottleneck_detector import BottleneckDetector
from analyzers.race_detector import RaceConditionDetector
from analyzers.report_generator import ReportGenerator

from gui.animated_canvas import AnimatedCanvas
from gui.metrics_panel import MetricsPanel
from gui.log_panel import LogPanel
from gui.timeline_panel import TimelinePanel
from gui.message_browser import MessageBrowser
from gui.settings_panel import SettingsPanel
from gui.tooltip import ToolTip
from gui.simulation_controller import SimulationController
from gui import scenarios

C = COLORS  # shorthand


def _make_button(parent, text, bg, hover_bg, command, **kw):
    """Create a styled flat button with hover effect and rounded feel."""
    btn = tk.Button(
        parent, text=text, font=kw.get("font", ("Segoe UI", 10, "bold")),
        bg=bg, fg=kw.get("fg", "#fff"), activebackground=hover_bg,
        activeforeground="#fff", relief="flat", cursor="hand2",
        padx=kw.get("padx", 16), pady=kw.get("pady", 7),
        command=command, bd=0,
    )
    btn.bind("<Enter>", lambda e: btn.config(bg=hover_bg))
    btn.bind("<Leave>", lambda e: btn.config(bg=bg))
    return btn


class IPCDebuggerGUI:
    """Modern tab-based IPC Debugger dashboard."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.configure(bg=C["bg"])
        self.root.minsize(1400, 850)

        # ── Core modules ──
        self.logger = EventLogger()
        self.sync_manager = SynchronizationManager(self.logger)
        self.process_engine = ProcessEngine(self.logger)
        self.deadlock_detector = DeadlockDetector(self.sync_manager, self.logger)
        self.bottleneck_detector = BottleneckDetector(self.logger)
        self.race_detector = RaceConditionDetector(self.logger)
        self.report_generator = ReportGenerator(self.logger)

        # ── Data ──
        self.channels: List[IPCChannel] = []
        self.connections: List[dict] = []
        self.process_configs: Dict[str, ProcessConfig] = {}
        self.auto_deadlock_var = tk.BooleanVar(value=False)

        # ── Simulation Controller (Fix #20) ──
        self.sim_ctrl = SimulationController(
            root=self.root,
            engine=self.process_engine,
            sync_manager=self.sync_manager,
            logger=self.logger,
            deadlock_detector=self.deadlock_detector,
            bottleneck_detector=self.bottleneck_detector,
            race_detector=self.race_detector,
        )
        # Share data references
        self.sim_ctrl.channels = self.channels
        self.sim_ctrl.connections = self.connections
        self.sim_ctrl.process_configs = self.process_configs
        self.sim_ctrl.auto_deadlock_var = self.auto_deadlock_var

        # ── Build UI ──
        self._setup_styles()
        self._build_header()
        self._build_main_content()
        self._build_log_area()
        self._register_log_callback()

        # Wire controller → UI refresh callbacks (before first refresh)
        self.sim_ctrl.animated_canvas = self.animated_canvas
        self.sim_ctrl.metrics_panel = self.metrics_panel
        self.sim_ctrl.log_panel = self.log_panel
        self.sim_ctrl._refresh_canvas_fn = self._refresh_canvas
        self.sim_ctrl._refresh_process_cards_fn = self._refresh_process_cards
        self.sim_ctrl._refresh_connection_cards_fn = self._refresh_connection_cards
        self.sim_ctrl._update_pid_lists_fn = self._update_pid_lists

        # Wire process engine to canvas for tooltip stats
        self.animated_canvas._process_engine = self.process_engine

        # Wire pulse animations to send/receive events
        def _on_event_pulse(event):
            if event.action == "SEND" and event.source_pid and event.dest_pid:
                self.animated_canvas.pulse_edge(event.source_pid, event.dest_pid)
        self.logger.on('new_event', _on_event_pulse)

        # Initial canvas draw (now safe — animated_canvas is wired)
        self._refresh_canvas()

        # ── Keyboard Shortcuts (Fix #12) ──
        root.bind("<Control-s>", lambda e: self.sim_ctrl.start_simulation())
        root.bind("<Control-p>", lambda e: self.sim_ctrl.pause_simulation())
        root.bind("<Control-r>", lambda e: self.sim_ctrl.reset_all())
        root.bind("<Control-d>", lambda e: self.sim_ctrl.detect_deadlock())
        root.bind("<Control-b>", lambda e: self.sim_ctrl.analyze_bottlenecks())

    # ════════════════════════════════════════════
    # STYLES
    # ════════════════════════════════════════════
    def _setup_styles(self) -> None:
        style = ttk.Style()
        style.theme_use('clam')

        # Notebook: clean dark tabs with strong selection contrast
        style.configure("TNotebook", background=C["bg"], borderwidth=0,
                        tabmargins=[2, 4, 2, 0])
        style.configure("TNotebook.Tab",
                        background="#1e293b",
                        foreground="#94a3b8",
                        font=("Segoe UI", 8, "bold"),
                        padding=[4, 5])
        style.map("TNotebook.Tab",
                  background=[("selected", "#2563eb")],
                  foreground=[("selected", "#ffffff")],
                  expand=[("selected", [1, 1, 1, 0])])
        style.configure("TFrame", background=C["bg"])

        # Combobox dark theme styling
        style.map("TCombobox",
                  fieldbackground=[("readonly", "#1e2030")],
                  foreground=[("readonly", "#cdd6f4")],
                  background=[("readonly", "#1e2030")])
        self.root.option_add("*TCombobox*Listbox.background", "#1e2030")
        self.root.option_add("*TCombobox*Listbox.foreground", "#cdd6f4")
        self.root.option_add("*TCombobox*Listbox.selectBackground", "#313244")

    # ════════════════════════════════════════════
    # HEADER BAR
    # ════════════════════════════════════════════
    def _build_header(self) -> None:
        # Gradient-style header with two-tone background
        header_outer = tk.Frame(self.root, bg="#0c1425", height=64)
        header_outer.pack(fill="x")
        header_outer.pack_propagate(False)

        header = tk.Frame(header_outer, bg="#0c1425")
        header.pack(fill="both", expand=True, padx=12)

        # Title with icon
        title_frame = tk.Frame(header, bg="#0c1425")
        title_frame.pack(side="left")
        tk.Label(title_frame, text="IPC Debugger & Visualization Tool",
                 font=("Segoe UI", 16, "bold"), bg="#0c1425",
                 fg="#f1f5f9").pack(side="left", padx=(8, 0))
        tk.Label(title_frame, text="v2.0",
                 font=("Segoe UI", 9), bg="#0c1425",
                 fg="#64748b").pack(side="left", padx=(8, 0), pady=(4, 0))

        # Right side: speed + buttons + status
        right = tk.Frame(header, bg="#0c1425")
        right.pack(side="right")

        # Status indicator (far right)
        self._status_label = tk.Label(
            right, text="  Idle  ", font=("Segoe UI", 10, "bold"),
            bg="#1e293b", fg="#94a3b8", padx=12, pady=4)
        self._status_label.pack(side="right", padx=(12, 4))
        self.sim_ctrl.status_label = self._status_label

        # Separator line between status and buttons
        tk.Frame(right, bg="#334155", width=1).pack(side="right", fill="y", padx=4, pady=8)

        # Buttons group — with spacers for visual grouping
        _make_button(right, "Reset", C["btn_secondary"],
                     C["btn_secondary_hover"], self.sim_ctrl.reset_all,
                     font=("Segoe UI", 9, "bold")).pack(side="right", padx=3)

        tk.Frame(right, bg="#334155", width=1).pack(side="right", fill="y", padx=4, pady=8)

        _make_button(right, "Stop", C["btn_danger"],
                     C["btn_danger_hover"], self.sim_ctrl.stop_simulation,
                     font=("Segoe UI", 9, "bold")).pack(side="right", padx=3)

        self._pause_btn = _make_button(
            right, "Pause", C["btn_warning"],
            C["btn_warning_hover"], self.sim_ctrl.pause_simulation,
            font=("Segoe UI", 9, "bold"))
        self._pause_btn.pack(side="right", padx=3)
        self.sim_ctrl.pause_btn = self._pause_btn

        _make_button(right, "Start", C["btn_success"],
                     C["btn_success_hover"], self.sim_ctrl.start_simulation,
                     font=("Segoe UI", 9, "bold")).pack(side="right", padx=3)

        _make_button(right, "Step", C["btn_primary"],
                     C["btn_primary_hover"], self.sim_ctrl.step_simulation,
                     font=("Segoe UI", 9, "bold")).pack(side="right", padx=3)

        tk.Frame(right, bg="#334155", width=1).pack(side="right", fill="y", padx=4, pady=8)

        # Speed control — wider and clearer
        speed_frame = tk.Frame(right, bg="#0c1425")
        speed_frame.pack(side="right", padx=6)
        tk.Label(speed_frame, text="Speed", font=("Segoe UI", 9, "bold"),
                 bg="#0c1425", fg="#94a3b8").pack(side="left", padx=(0, 4))
        self._speed_var = tk.DoubleVar(value=1.0)
        self.sim_ctrl.speed_var = self._speed_var
        speed_scale = tk.Scale(speed_frame, from_=0.25, to=5.0, resolution=0.25,
                                orient="horizontal", variable=self._speed_var,
                                font=("Segoe UI", 8), bg="#0c1425",
                                fg="#e2e8f0", highlightthickness=0,
                                troughcolor="#334155",
                                activebackground=C["accent"],
                                length=160, showvalue=True, sliderlength=20)
        speed_scale.pack(side="left")

        # Accent divider (thicker gradient feel)
        divider = tk.Frame(self.root, height=3, bg=C["accent"])
        divider.pack(fill="x")

    # ════════════════════════════════════════════
    # MAIN CONTENT: Tabs + Canvas
    # ════════════════════════════════════════════
    def _build_main_content(self) -> None:
        # PanedWindow for resizable canvas/log split
        self._main_pane = tk.PanedWindow(
            self.root, orient=tk.VERTICAL, sashrelief=tk.RAISED,
            sashwidth=6, bg="#475569", opaqueresize=True)
        self._main_pane.pack(fill="both", expand=True)

        # Upper area: tabs + canvas (gets most of the space)
        upper = tk.Frame(self._main_pane, bg=C["bg"])
        self._main_pane.add(upper, minsize=400, stretch="always")

        main = tk.Frame(upper, bg=C["bg"])
        main.pack(fill="both", expand=True)

        # LEFT: Tab panel — wider for readable labels
        left = tk.Frame(main, bg=C["bg"], width=380)
        left.pack(side="left", fill="y", padx=(6, 0), pady=6)
        left.pack_propagate(False)
        self._build_tabs(left)

        # Separator line
        tk.Frame(main, bg="#475569", width=2).pack(side="left", fill="y", pady=8)

        # RIGHT: Canvas + Metrics
        right = tk.Frame(main, bg=C["bg"])
        right.pack(side="left", fill="both", expand=True, padx=(4, 6), pady=6)

        canvas_frame = tk.Frame(right, bg=C["panel_bg"], relief="flat",
                                highlightthickness=1, highlightbackground="#334155")
        canvas_frame.pack(fill="both", expand=True)
        self.animated_canvas = AnimatedCanvas(canvas_frame)

        metrics_frame = tk.Frame(right, bg=C["bg"])
        metrics_frame.pack(fill="x")
        self.metrics_panel = MetricsPanel(metrics_frame)

    # ════════════════════════════════════════════
    # TABS
    # ════════════════════════════════════════════
    def _build_tabs(self, parent) -> None:
        nb = ttk.Notebook(parent)
        nb.pack(fill="both", expand=True)

        # Short tab labels to fit all 7 in sidebar
        tabs = [
            ("Proc", self._build_process_tab),
            ("Conn", self._build_connection_tab),
            ("Anlz", self._build_analysis_tab),
            ("Scen", self._build_scenario_tab),
        ]
        for title, builder in tabs:
            frame = tk.Frame(nb, bg=C["bg"])
            builder(frame)
            nb.add(frame, text=title)

        # Timeline tab
        tl_frame = tk.Frame(nb, bg=C["bg"])
        self.timeline_panel = TimelinePanel(tl_frame)
        self.timeline_panel.show()
        tl_btn_frame = tk.Frame(tl_frame, bg=C["bg"])
        tl_btn_frame.pack(fill="x", padx=8, pady=4)
        _make_button(tl_btn_frame, "Refresh Timeline",
                     C["btn_primary"], C["btn_primary_hover"],
                     self._refresh_timeline,
                     font=("Segoe UI", 9, "bold")).pack(fill="x")
        nb.add(tl_frame, text="Time")

        # Messages tab
        msg_frame = tk.Frame(nb, bg=C["bg"])
        self.message_browser = MessageBrowser(msg_frame)
        msg_btn_frame = tk.Frame(msg_frame, bg=C["bg"])
        msg_btn_frame.pack(fill="x", padx=8, pady=4)
        _make_button(msg_btn_frame, "Refresh Messages",
                     C["btn_primary"], C["btn_primary_hover"],
                     self._refresh_messages,
                     font=("Segoe UI", 9, "bold")).pack(fill="x")
        nb.add(msg_frame, text="Msgs")

        # Settings tab
        settings_frame = tk.Frame(nb, bg=C["bg"])
        self.settings_panel = SettingsPanel(settings_frame)
        self.settings_panel.auto_deadlock_var = self.auto_deadlock_var
        nb.add(settings_frame, text="Cfg")

    # ── PROCESS TAB ──
    def _build_process_tab(self, parent) -> None:
        # Add Process card
        card = tk.Frame(parent, bg=C["panel_bg"], padx=16, pady=12)
        card.pack(fill="x", padx=8, pady=(8, 4))

        tk.Label(card, text="\u2795 Add New Process", font=("Segoe UI", 12, "bold"),
                 bg=C["panel_bg"], fg=C["accent"]).pack(anchor="w")
        tk.Frame(card, bg=C["card_bg"], height=1).pack(fill="x", pady=(6, 10))

        fields = tk.Frame(card, bg=C["panel_bg"])
        fields.pack(fill="x")

        def _field(label, row, default="", widget_type="entry", values=None):
            tk.Label(fields, text=label, font=("Segoe UI", 10),
                     bg=C["panel_bg"], fg=C["text_muted"]).grid(
                row=row, column=0, sticky="w", padx=(0, 8), pady=3)
            if widget_type == "entry":
                w = tk.Entry(fields, font=("Segoe UI", 10), width=18,
                             bg=C["card_bg"], fg=C["text"],
                             insertbackground=C["text"], relief="flat",
                             highlightthickness=1, highlightcolor=C["accent"],
                             highlightbackground=C["text_dim"])
                w.insert(0, default)
            elif widget_type == "combo":
                w = ttk.Combobox(fields, values=values, state="readonly",
                                 width=16, font=("Segoe UI", 10))
                w.set(default)
            elif widget_type == "spin":
                w = tk.Spinbox(fields, from_=1, to=10, width=6,
                               font=("Segoe UI", 10), bg=C["card_bg"],
                               fg=C["text"], buttonbackground=C["card_bg"],
                               relief="flat", highlightthickness=1,
                               highlightcolor=C["accent"],
                               highlightbackground=C["text_dim"])
                w.delete(0, "end")
                w.insert(0, default)
            w.grid(row=row, column=1, sticky="ew", pady=3)
            fields.columnconfigure(1, weight=1)
            return w

        self.entry_pid = _field("Process ID", 0)
        self.combo_behavior = _field("Behavior", 1, "producer", "combo",
                                     ["producer", "consumer", "producer_consumer"])
        self.entry_message = _field("Message", 2, "Hello")
        self.entry_delay = _field("Delay (s)", 3, "1.0")
        self.spin_priority = _field("Priority", 4, "5", "spin")

        ToolTip(self.entry_pid, "Unique name for this process (e.g. P1, Producer_A)")
        ToolTip(self.combo_behavior, "Producer: sends | Consumer: receives | Both: send+receive")
        ToolTip(self.entry_delay, "Seconds between each operation cycle")

        _make_button(card, "\u2795 Add Process", C["btn_primary"],
                     C["btn_primary_hover"], self._on_add_process
                     ).pack(fill="x", pady=(10, 0))

        # Active Process Cards container
        tk.Label(parent, text="Active Processes", font=("Segoe UI", 11, "bold"),
                 bg=C["bg"], fg=C["text"]).pack(anchor="w", padx=16, pady=(12, 4))
        tk.Frame(parent, bg=C["card_bg"], height=1).pack(fill="x", padx=16)

        # Fix #8: Add visible scrollbar for process cards
        scroll_container = tk.Frame(parent, bg=C["bg"])
        scroll_container.pack(fill="both", expand=True, padx=8, pady=4)

        self._card_scroll = tk.Canvas(scroll_container, bg=C["bg"], highlightthickness=0)
        card_scrollbar = ttk.Scrollbar(scroll_container, orient="vertical",
                                       command=self._card_scroll.yview)
        self._card_scroll.configure(yscrollcommand=card_scrollbar.set)

        self._card_scroll.pack(side="left", fill="both", expand=True)
        card_scrollbar.pack(side="right", fill="y")

        self._card_inner = tk.Frame(self._card_scroll, bg=C["bg"])
        self._card_scroll.create_window((0, 0), window=self._card_inner, anchor="nw")
        self._card_inner.bind("<Configure>",
            lambda e: self._card_scroll.configure(
                scrollregion=self._card_scroll.bbox("all")))
        # MouseWheel scroll binding
        self._card_scroll.bind("<MouseWheel>",
            lambda e: self._card_scroll.yview_scroll(-1*(e.delta//120), "units"))

        # Fix #17: Synchronization Primitives section
        tk.Label(parent, text="\U0001f512 Synchronization Primitives",
                 font=("Segoe UI", 11, "bold"),
                 bg=C["bg"], fg=C["text"]).pack(anchor="w", padx=16, pady=(8, 4))
        tk.Frame(parent, bg=C["card_bg"], height=1).pack(fill="x", padx=16)

        sem_card = tk.Frame(parent, bg=C["panel_bg"], padx=12, pady=8)
        sem_card.pack(fill="x", padx=8, pady=4)

        sem_fields = tk.Frame(sem_card, bg=C["panel_bg"])
        sem_fields.pack(fill="x")

        tk.Label(sem_fields, text="Name:", font=("Segoe UI", 9),
                 bg=C["panel_bg"], fg=C["text_muted"]).grid(
            row=0, column=0, sticky="w", padx=(0, 4))
        self.entry_sem_name = tk.Entry(sem_fields, font=("Segoe UI", 9), width=12,
                                       bg=C["card_bg"], fg=C["text"],
                                       insertbackground=C["text"], relief="flat")
        self.entry_sem_name.grid(row=0, column=1, sticky="ew", padx=2)

        tk.Label(sem_fields, text="Value:", font=("Segoe UI", 9),
                 bg=C["panel_bg"], fg=C["text_muted"]).grid(
            row=0, column=2, sticky="w", padx=(8, 4))
        self.spin_sem_value = tk.Spinbox(sem_fields, from_=1, to=10, width=4,
                                         font=("Segoe UI", 9), bg=C["card_bg"],
                                         fg=C["text"], relief="flat")
        self.spin_sem_value.delete(0, "end")
        self.spin_sem_value.insert(0, "1")
        self.spin_sem_value.grid(row=0, column=3, padx=2)
        sem_fields.columnconfigure(1, weight=1)

        _make_button(sem_card, "\u2795 Add Semaphore", C["btn_secondary"],
                     C["btn_secondary_hover"], self._on_add_semaphore,
                     font=("Segoe UI", 9), padx=6, pady=3
                     ).pack(fill="x", pady=(6, 0))

        self._sem_list = tk.Frame(parent, bg=C["bg"])
        self._sem_list.pack(fill="x", padx=8, pady=2)

    # ── CONNECTION TAB ──
    def _build_connection_tab(self, parent) -> None:
        card = tk.Frame(parent, bg=C["panel_bg"], padx=16, pady=12)
        card.pack(fill="x", padx=8, pady=8)

        tk.Label(card, text="\U0001f517 Add Connection", font=("Segoe UI", 12, "bold"),
                 bg=C["panel_bg"], fg=C["accent"]).pack(anchor="w")
        tk.Frame(card, bg=C["card_bg"], height=1).pack(fill="x", pady=(6, 10))

        fields = tk.Frame(card, bg=C["panel_bg"])
        fields.pack(fill="x")

        def _combo_field(label, row):
            tk.Label(fields, text=label, font=("Segoe UI", 10),
                     bg=C["panel_bg"], fg=C["text_muted"]).grid(
                row=row, column=0, sticky="w", padx=(0, 8), pady=4)
            w = ttk.Combobox(fields, values=[], state="readonly",
                             width=16, font=("Segoe UI", 10))
            w.grid(row=row, column=1, sticky="ew", pady=4)
            fields.columnconfigure(1, weight=1)
            return w

        self.combo_source = _combo_field("Source", 0)
        self.combo_dest = _combo_field("Destination", 1)
        self.combo_channel = _combo_field("Channel Type", 2)
        self.combo_channel['values'] = ["pipe", "queue", "shared_memory"]
        self.combo_channel.set("queue")

        ToolTip(self.combo_source, "Process that sends messages")
        ToolTip(self.combo_dest, "Process that receives messages")
        ToolTip(self.combo_channel, "pipe: 1-to-1 | queue: FIFO buffer | shared_memory: direct access")

        _make_button(card, "\U0001f517 Add Connection", C["btn_primary"],
                     C["btn_primary_hover"], self._on_add_connection
                     ).pack(fill="x", pady=(10, 0))

        # Active connections display
        tk.Label(parent, text="Active Connections", font=("Segoe UI", 11, "bold"),
                 bg=C["bg"], fg=C["text"]).pack(anchor="w", padx=16, pady=(12, 4))
        self._conn_list = tk.Frame(parent, bg=C["bg"])
        self._conn_list.pack(fill="both", expand=True, padx=8)

    # ── ANALYSIS TAB ──
    def _build_analysis_tab(self, parent) -> None:
        scroll = tk.Canvas(parent, bg=C["bg"], highlightthickness=0)
        scroll.pack(fill="both", expand=True)
        inner = tk.Frame(scroll, bg=C["bg"])
        scroll.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
            lambda e: scroll.configure(scrollregion=scroll.bbox("all")))

        def _tool_card(title, desc, btn_text, btn_color, btn_hover, cmd, extra_builder=None):
            card = tk.Frame(inner, bg=C["panel_bg"], padx=14, pady=10)
            card.pack(fill="x", padx=8, pady=4)
            tk.Label(card, text=title, font=("Segoe UI", 11, "bold"),
                     bg=C["panel_bg"], fg=C["text"]).pack(anchor="w")
            tk.Label(card, text=desc, font=("Segoe UI", 9),
                     bg=C["panel_bg"], fg=C["text_muted"], wraplength=300,
                     justify="left").pack(anchor="w", pady=(2, 6))
            if extra_builder:
                extra_builder(card)
            _make_button(card, btn_text, btn_color, btn_hover, cmd,
                         font=("Segoe UI", 9, "bold")).pack(fill="x")

        _tool_card(
            "\U0001f534 Deadlock Detection",
            "Build Wait-For Graph and detect all circular dependencies",
            "Run Detection", C["btn_danger"], C["btn_danger_hover"],
            self.sim_ctrl.detect_deadlock,
            extra_builder=lambda card: tk.Checkbutton(
                card, text="Auto-detect (every 2s)", variable=self.auto_deadlock_var,
                bg=C["panel_bg"], fg=C["text_muted"], selectcolor=C["card_bg"],
                activebackground=C["panel_bg"], activeforeground=C["text"],
                font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 6))
        )

        def _threshold_fields(card):
            tf = tk.Frame(card, bg=C["panel_bg"])
            tf.pack(fill="x", pady=(0, 6))
            for i, (lbl, attr, default) in enumerate([
                ("Depth:", "entry_thresh_depth", "10"),
                ("Latency:", "entry_thresh_latency", "2.0"),
                ("Ratio:", "entry_thresh_ratio", "0.5")]):
                tk.Label(tf, text=lbl, font=("Segoe UI", 9), bg=C["panel_bg"],
                         fg=C["text_dim"]).grid(row=0, column=i*2, padx=(0, 2))
                e = tk.Entry(tf, width=5, font=("Segoe UI", 9), bg=C["card_bg"],
                             fg=C["text"], relief="flat", insertbackground=C["text"])
                e.insert(0, default)
                e.grid(row=0, column=i*2+1, padx=(0, 8))
                setattr(self, attr, e)
            # Wire threshold entries to controller
            self.sim_ctrl.entry_thresh_depth = self.entry_thresh_depth
            self.sim_ctrl.entry_thresh_latency = self.entry_thresh_latency
            self.sim_ctrl.entry_thresh_ratio = self.entry_thresh_ratio

        _tool_card(
            "\U0001f4ca Bottleneck Analysis",
            "Check queue depths, latency, and throughput ratios",
            "Analyze", C["btn_warning"], C["btn_warning_hover"],
            self.sim_ctrl.analyze_bottlenecks,
            extra_builder=_threshold_fields
        )

        _tool_card(
            "\u26a1 Race Condition Detection",
            "Detect concurrent access to shared resources without locks",
            "Detect Races", C["btn_danger"], C["btn_danger_hover"],
            self.sim_ctrl.detect_races
        )

        _tool_card(
            "\U0001f4c8 Performance Metrics",
            "Show latency, throughput, and queue depth charts",
            "Show Metrics", C["btn_primary"], C["btn_primary_hover"],
            self.sim_ctrl.show_metrics
        )

    # ── SCENARIO TAB ──
    def _build_scenario_tab(self, parent) -> None:
        # Scrollable scenario list
        scen_scroll = tk.Canvas(parent, bg=C["bg"], highlightthickness=0)
        scen_scroll.pack(fill="both", expand=True)
        scen_inner = tk.Frame(scen_scroll, bg=C["bg"])
        scen_scroll.create_window((0, 0), window=scen_inner, anchor="nw")
        scen_inner.bind("<Configure>",
            lambda e: scen_scroll.configure(scrollregion=scen_scroll.bbox("all")))
        scen_scroll.bind("<MouseWheel>",
            lambda e: scen_scroll.yview_scroll(-1*(e.delta//120), "units"))

        scens = [
            ("\U0001f4e6 Normal IPC", "Producer \u2192 Consumer",
             "A producer sends messages to a consumer\nvia a queue channel. Great for basics.",
             C["btn_primary"], C["btn_primary_hover"], scenarios.load_normal_ipc),
            ("\U0001f534 Deadlock Scenario", "3 Processes \u2192 Circular Locks",
             "Three processes with circular lock\ndependencies. Demonstrates WFG cycle detection.",
             C["btn_danger"], C["btn_danger_hover"], scenarios.load_deadlock),
            ("\U0001f4ca Bottleneck Scenario", "Fast \u2192 Slow",
             "A fast producer overwhelms a slow\nconsumer. Queue fills up over time.",
             C["btn_warning"], C["btn_warning_hover"], scenarios.load_bottleneck),
            ("\u26a1 Race Condition", "3 Writers \u2192 Shared Memory",
             "Three writers concurrently access shared\nmemory without locks. Detects data races.",
             C["btn_danger"], C["btn_danger_hover"], scenarios.load_race_condition),
            ("\U0001f517 Pipeline", "Source \u2192 Stage1 \u2192 Stage2 \u2192 Sink",
             "Multi-stage pipeline using pipe, queue,\nand shared memory. Mixed IPC demonstration.",
             C["btn_success"], C["btn_success_hover"], scenarios.load_pipeline),
        ]
        for title, subtitle, desc, color, hover, loader in scens:
            card = tk.Frame(scen_inner, bg=C["panel_bg"], padx=16, pady=12)
            card.pack(fill="x", padx=8, pady=4)
            tk.Label(card, text=title, font=("Segoe UI", 12, "bold"),
                     bg=C["panel_bg"], fg=C["text"]).pack(anchor="w")
            tk.Label(card, text=subtitle, font=("Segoe UI", 10),
                     bg=C["panel_bg"], fg=C["accent"]).pack(anchor="w")
            tk.Label(card, text=desc, font=("Segoe UI", 9),
                     bg=C["panel_bg"], fg=C["text_muted"], justify="left"
                     ).pack(anchor="w", pady=(4, 8))
            _make_button(card, "Load & Run", color, hover,
                         lambda fn=loader: self._load_and_run_scenario(fn),
                         font=("Segoe UI", 10, "bold")).pack(fill="x")

        tk.Frame(scen_inner, bg=C["bg"], height=16).pack()
        _make_button(scen_inner, "\U0001f504 Reset Everything",
                     C["btn_secondary"], C["btn_secondary_hover"],
                     self.sim_ctrl.reset_all).pack(fill="x", padx=24)

        # Export section
        tk.Label(scen_inner, text="\U0001f4be Export", font=("Segoe UI", 11, "bold"),
                 bg=C["bg"], fg=C["text"]).pack(anchor="w", padx=16, pady=(16, 4))
        export_frame = tk.Frame(scen_inner, bg=C["bg"])
        export_frame.pack(fill="x", padx=16)
        for text, cmd in [("HTML Report", self._export_html_report),
                          ("CSV Log", self._export_log_csv),
                          ("PNG Graph", self._save_graph_png),
                          ("Metrics", self._export_metrics_report)]:
            _make_button(export_frame, text, C["btn_secondary"],
                         C["btn_secondary_hover"], cmd,
                         font=("Segoe UI", 9), padx=8, pady=4
                         ).pack(side="left", padx=2, fill="x", expand=True)

    # ════════════════════════════════════════════
    # LOG AREA (Fix #11: PanedWindow for resizable log area)
    # ════════════════════════════════════════════
    def _build_log_area(self) -> None:
        log_frame = tk.Frame(self._main_pane, bg=C["panel_bg"],
                             highlightthickness=1, highlightbackground="#334155")
        # Log panel gets less space — max 180px initially, resizable
        self._main_pane.add(log_frame, minsize=100, height=170, stretch="never")
        self.log_panel = LogPanel(log_frame)

    # ════════════════════════════════════════════
    # LOG CALLBACK
    # ════════════════════════════════════════════
    def _register_log_callback(self) -> None:
        def on_event(event: LogEvent):
            self.root.after(0, self.log_panel.append, event)
        self.logger.on('new_event', on_event)

    # ════════════════════════════════════════════
    # PROCESS CARDS
    # ════════════════════════════════════════════
    def _refresh_process_cards(self) -> None:
        for w in self._card_inner.winfo_children():
            w.destroy()
        if not self.process_configs:
            tk.Label(self._card_inner, text="No processes yet.\nAdd one above!",
                     font=("Segoe UI", 10), bg=C["bg"], fg=C["text_dim"]
                     ).pack(pady=20)
            return
        for pid, cfg in self.process_configs.items():
            proc = self.process_engine.get_process(pid)
            self._create_process_card(self._card_inner, pid, cfg, proc)
        # Also refresh semaphore list
        self._refresh_semaphore_list()

    def _create_process_card(self, parent, pid: str, cfg: ProcessConfig,
                             proc) -> None:
        state = proc.state if proc else "idle"
        behavior = cfg.behavior
        icon = BEHAVIOR_ICONS.get(behavior, "\u2022")
        st_icon = STATE_ICONS.get(state, "\u25cb")
        st_color = COLORS.get(state, C["text_muted"])
        border_color = COLORS.get(behavior, C["accent"])

        card = tk.Frame(parent, bg=C["panel_bg"], padx=12, pady=8,
                        highlightbackground=border_color, highlightthickness=2)
        card.pack(fill="x", padx=4, pady=3)

        top = tk.Frame(card, bg=C["panel_bg"])
        top.pack(fill="x")
        tk.Label(top, text=f"{icon} {pid}", font=("Segoe UI", 11, "bold"),
                 bg=C["panel_bg"], fg=C["text"]).pack(side="left")
        tk.Label(top, text=f"{st_icon} {state.upper()}", font=("Segoe UI", 9, "bold"),
                 bg=C["panel_bg"], fg=st_color).pack(side="right")

        info = tk.Frame(card, bg=C["panel_bg"])
        info.pack(fill="x", pady=(4, 0))
        tk.Label(info, text=f"{behavior}  |  pri={cfg.priority}  |  delay={cfg.delay}s",
                 font=("Segoe UI", 8), bg=C["panel_bg"], fg=C["text_dim"]).pack(side="left")

        if proc:
            stats = tk.Frame(card, bg=C["panel_bg"])
            stats.pack(fill="x", pady=(2, 0))
            tk.Label(stats, text=f"\u2191 {proc.messages_sent} sent",
                     font=("Segoe UI", 9), bg=C["panel_bg"], fg=C["accent_ok"]
                     ).pack(side="left", padx=(0, 12))
            tk.Label(stats, text=f"\u2193 {proc.messages_received} recv",
                     font=("Segoe UI", 9), bg=C["panel_bg"], fg=C["accent"]
                     ).pack(side="left")

        rm_btn = tk.Button(
            card, text="\u2716", font=("Segoe UI", 10), bg=C["panel_bg"],
            fg=C["accent_err"], relief="flat", cursor="hand2", bd=0,
            activebackground=C["panel_bg"], activeforeground="#fff",
            command=lambda p=pid: self._on_remove_process(p))
        rm_btn.place(relx=1.0, rely=0, anchor="ne", x=-4, y=4)

    def _refresh_connection_cards(self) -> None:
        for w in self._conn_list.winfo_children():
            w.destroy()
        for i, conn in enumerate(self.connections):
            c = tk.Frame(self._conn_list, bg=C["panel_bg"], padx=10, pady=6)
            c.pack(fill="x", pady=2)
            ch_color = COLORS.get(conn["channel_type"], C["accent"])
            tk.Label(c, text=f"{conn['source']} \u2192 {conn['dest']}",
                     font=("Segoe UI", 10, "bold"), bg=C["panel_bg"],
                     fg=C["text"]).pack(side="left")
            tk.Label(c, text=f"  {conn['channel_type']}",
                     font=("Segoe UI", 9), bg=C["panel_bg"], fg=ch_color
                     ).pack(side="left", padx=4)
            # Fix #7: Add connection removal button
            rm_btn = tk.Button(
                c, text="\u00d7", font=("Segoe UI", 12, "bold"),
                bg=C["panel_bg"], fg="#e74c3c", relief="flat",
                cursor="hand2", bd=0,
                activebackground=C["panel_bg"], activeforeground="#fff",
                command=lambda idx=i: self._remove_connection(idx))
            rm_btn.pack(side="right")

    # ════════════════════════════════════════════
    # CALLBACKS: Process Management
    # ════════════════════════════════════════════
    def _on_add_process(self) -> None:
        pid = self.entry_pid.get().strip()
        if not pid:
            messagebox.showwarning("Validation", "Process ID cannot be empty.")
            return
        if pid in self.process_configs:
            messagebox.showwarning("Validation", f"Process '{pid}' already exists.")
            return
        try:
            priority = max(1, min(10, int(self.spin_priority.get())))
        except ValueError:
            priority = 5
        behavior = self.combo_behavior.get()
        message = self.entry_message.get().strip() or "Hello"
        try:
            delay = float(self.entry_delay.get())
        except ValueError:
            delay = 1.0

        cfg = ProcessConfig(pid=pid, priority=priority, behavior=behavior,
                            message=message, delay=delay)
        self.process_configs[pid] = cfg
        self.process_engine.add_process(cfg)
        self._update_pid_lists()
        self.logger.log_event(source_pid=pid, dest_pid="", action="INFO",
            details=f"Process added: {behavior}, pri={priority}, delay={delay}s")
        self._refresh_canvas()
        self._refresh_process_cards()
        self.entry_pid.delete(0, tk.END)

    def _on_remove_process(self, pid: str) -> None:
        if pid not in self.process_configs:
            return
        self.process_engine.remove_process(pid)
        to_remove = [i for i, ch in enumerate(self.channels)
                     if ch.source_pid == pid or ch.dest_pid == pid]
        for i in reversed(to_remove):
            self.channels[i].close()
            self.channels.pop(i)
        # Mutate in-place to preserve shared reference with sim_ctrl
        self.connections[:] = [c for c in self.connections
                               if c["source"] != pid and c["dest"] != pid]
        for cfg in self.process_configs.values():
            cfg.send_channels = [ch for ch in cfg.send_channels
                                 if ch.source_pid != pid and ch.dest_pid != pid]
            cfg.recv_channels = [ch for ch in cfg.recv_channels
                                 if ch.source_pid != pid and ch.dest_pid != pid]
        del self.process_configs[pid]
        self._update_pid_lists()
        self.logger.log_event(source_pid=pid, dest_pid="", action="INFO",
                              details="Process removed")
        self._refresh_canvas()
        self._refresh_process_cards()
        self._refresh_connection_cards()

    def _on_add_connection(self) -> None:
        src = self.combo_source.get().strip()
        dst = self.combo_dest.get().strip()
        ch_type = self.combo_channel.get().strip()
        if not src or not dst:
            messagebox.showwarning("Validation", "Select both source and destination.")
            return
        if src == dst:
            messagebox.showwarning("Validation", "Source and destination must differ.")
            return
        for c in self.connections:
            if c["source"] == src and c["dest"] == dst:
                messagebox.showwarning("Validation", f"Connection {src}\u2192{dst} exists.")
                return
        ch_name = f"{src}_{dst}_{ch_type}"
        # Fix #1: Pass race_detector to create_channel
        channel = create_channel(ch_type, ch_name, src, dst, self.logger,
                                 race_detector=self.race_detector)
        self.channels.append(channel)
        self.connections.append({"source": src, "dest": dst,
                                 "channel_type": ch_type, "channel_name": ch_name})
        self.process_configs[src].send_channels.append(channel)
        self.process_configs[dst].recv_channels.append(channel)
        self.logger.log_event(source_pid=src, dest_pid=dst, action="INFO",
            details=f"Connection added: {ch_type}", channel_name=ch_name, channel_type=ch_type)
        self._refresh_canvas()
        self._refresh_connection_cards()

    # Fix #7: Connection removal
    def _remove_connection(self, conn_index: int) -> None:
        """Remove a connection by its index in self.connections."""
        if conn_index < 0 or conn_index >= len(self.connections):
            return
        conn = self.connections[conn_index]
        # Find and close the channel
        ch_name = conn["channel_name"]
        for i, ch in enumerate(self.channels):
            if ch.name == ch_name:
                ch.close()
                self.channels.pop(i)
                break
        # Remove from process configs
        src, dst = conn["source"], conn["dest"]
        if src in self.process_configs:
            self.process_configs[src].send_channels = [
                ch for ch in self.process_configs[src].send_channels
                if ch.name != ch_name]
        if dst in self.process_configs:
            self.process_configs[dst].recv_channels = [
                ch for ch in self.process_configs[dst].recv_channels
                if ch.name != ch_name]
        self.connections.pop(conn_index)
        self.logger.log_event(source_pid=src, dest_pid=dst, action="INFO",
                              details=f"Connection removed: {ch_name}")
        self._refresh_canvas()
        self._refresh_connection_cards()

    # Fix #17: Semaphore management
    def _on_add_semaphore(self) -> None:
        """Add a new semaphore via the sync manager."""
        name = self.entry_sem_name.get().strip()
        if not name:
            messagebox.showwarning("Validation", "Semaphore name cannot be empty.")
            return
        if self.sync_manager.get_semaphore(name):
            messagebox.showwarning("Validation", f"Semaphore '{name}' already exists.")
            return
        try:
            value = max(1, min(10, int(self.spin_sem_value.get())))
        except ValueError:
            value = 1
        self.sync_manager.create_semaphore(name, value)
        self.logger.log_event(source_pid="SYSTEM", dest_pid="", action="INFO",
                              details=f"Semaphore created: {name} (value={value})")
        self.entry_sem_name.delete(0, tk.END)
        self._refresh_semaphore_list()

    def _refresh_semaphore_list(self) -> None:
        """Refresh the displayed semaphore list."""
        for w in self._sem_list.winfo_children():
            w.destroy()
        for name, sem in self.sync_manager.semaphores.items():
            state = sem.get_state()
            row = tk.Frame(self._sem_list, bg=C["panel_bg"], padx=8, pady=4)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=f"\U0001f512 {name}",
                     font=("Segoe UI", 9, "bold"),
                     bg=C["panel_bg"], fg=C["text"]).pack(side="left")
            tk.Label(row,
                     text=f"  val={state['current_value']}/{state['max_value']}",
                     font=("Segoe UI", 8),
                     bg=C["panel_bg"], fg=C["text_dim"]).pack(side="left", padx=4)

    # ════════════════════════════════════════════
    # REFRESH
    # ════════════════════════════════════════════
    def _refresh_canvas(self) -> None:
        pids = list(self.process_configs.keys())
        states = self.process_engine.get_all_states()
        self.animated_canvas.update_topology(pids, self.connections, states)

    # ════════════════════════════════════════════
    # SCENARIOS
    # ════════════════════════════════════════════
    def _load_and_run_scenario(self, loader_fn) -> None:
        self._load_scenario(loader_fn)
        self.sim_ctrl.start_simulation()

    def _load_scenario(self, loader_fn) -> None:
        self.sim_ctrl.reset_all(force=True)
        configs, connections, lock_setup = loader_fn()
        for pid, cfg in configs.items():
            self.process_configs[pid] = cfg
            self.process_engine.add_process(cfg)
        if lock_setup:
            for pid, lock_names in lock_setup:
                locks = []
                for lname in lock_names:
                    lock = self.sync_manager.get_lock(lname) or self.sync_manager.create_lock(lname)
                    locks.append(lock)
                self.process_configs[pid].locks_to_acquire = locks
        for conn in connections:
            kw = {"maxsize": conn["maxsize"]} if "maxsize" in conn else {}
            # Fix #1: Pass race_detector when loading scenarios
            ch = create_channel(conn["channel_type"], conn["channel_name"],
                                conn["source"], conn["dest"], self.logger,
                                race_detector=self.race_detector, **kw)
            self.channels.append(ch)
            self.connections.append({k: conn[k] for k in ("source", "dest", "channel_type", "channel_name")})
            if conn["source"] in self.process_configs:
                self.process_configs[conn["source"]].send_channels.append(ch)
            if conn["dest"] in self.process_configs:
                self.process_configs[conn["dest"]].recv_channels.append(ch)
        self._update_pid_lists()
        self.logger.log_event(source_pid="SYSTEM", dest_pid="", action="INFO",
            details=f"Loaded: {(loader_fn.__doc__ or '').split(chr(10))[0]}")
        self._refresh_canvas()
        self._refresh_process_cards()
        self._refresh_connection_cards()

    # ════════════════════════════════════════════
    # EXPORT
    # ════════════════════════════════════════════
    def _export_html_report(self) -> None:
        """Generate and save a comprehensive HTML analysis report."""
        fp = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTML", "*.html")],
            title="Export HTML Report")
        if not fp:
            return
        # Collect analysis data
        metrics = self.bottleneck_detector.get_channel_metrics(self.channels) if self.channels else []
        bottlenecks = self.bottleneck_detector.analyze_channels(self.channels) if self.channels else []
        deadlock_cycles = self.deadlock_detector.last_cycles
        race_reports = self.race_detector.detect_races()
        events = self.logger.get_all_events()

        html = self.report_generator.generate_html_report(
            metrics, bottlenecks, deadlock_cycles, race_reports, events
        )
        with open(fp, 'w', encoding='utf-8') as f:
            f.write(html)
        messagebox.showinfo("Export", f"HTML Report saved to {fp}")

    def _export_log_csv(self) -> None:
        import csv
        fp = filedialog.asksaveasfilename(defaultextension=".csv",
            filetypes=[("CSV", "*.csv")], title="Export Log")
        if not fp:
            return
        events = self.logger.get_all_events()
        with open(fp, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(["timestamp", "source", "dest", "action", "size", "details", "channel", "type"])
            for e in events:
                w.writerow([f"{e.timestamp:.3f}", e.source_pid, e.dest_pid,
                            e.action, e.data_size, e.details, e.channel_name, e.channel_type])
        messagebox.showinfo("Export", f"Saved to {fp}")

    def _save_graph_png(self) -> None:
        """Fix #3: Save as real PNG using Matplotlib figure."""
        fp = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png")],
            title="Save Graph")
        if not fp:
            return
        try:
            fig = self.metrics_panel.fig
            fig.savefig(fp, dpi=150, bbox_inches='tight', facecolor='#0f0f23')
            messagebox.showinfo("Export", f"Saved to {fp}")
        except (OSError, RuntimeError) as e:
            self.logger.log_event(source_pid="SYSTEM", dest_pid="", action="WARNING",
                                  details=f"PNG export error: {e}")
            messagebox.showerror("Error", str(e))

    def _export_metrics_report(self) -> None:
        if not self.channels:
            messagebox.showinfo("Export", "No channels.")
            return
        fp = filedialog.asksaveasfilename(defaultextension=".txt",
            filetypes=[("Text", "*.txt")], title="Export Metrics")
        if not fp:
            return
        metrics = self.bottleneck_detector.get_channel_metrics(self.channels)
        with open(fp, 'w', encoding='utf-8') as f:
            f.write("IPC Debugger \u2014 Metrics Report\n" + "=" * 50 + "\n\n")
            for m in metrics:
                f.write(f"{m.name} ({m.channel_type}): {m.source}\u2192{m.dest}\n")
                f.write(f"  Sent={m.messages_sent} Recv={m.messages_received} "
                        f"Bytes={m.total_bytes}\n")
                f.write(f"  Latency: avg={m.avg_latency:.3f}s max={m.max_latency:.3f}s\n")
                f.write(f"  Throughput: {m.throughput:.2f}msg/s  "
                        f"Depth={m.queue_depth} Peak={m.peak_depth}\n\n")
        messagebox.showinfo("Export", f"Saved to {fp}")

    # ════════════════════════════════════════════
    # HELPERS
    # ════════════════════════════════════════════
    def _update_pid_lists(self) -> None:
        pids = list(self.process_configs.keys())
        self.combo_source['values'] = pids
        self.combo_dest['values'] = pids

    def _refresh_timeline(self) -> None:
        """Update the timeline panel with current event data."""
        events = self.logger.get_all_events()
        pids = list(self.process_configs.keys())
        self.timeline_panel.update_timeline(events, pids)

    def _refresh_messages(self) -> None:
        """Update the message browser with current events."""
        events = self.logger.get_all_events()
        self.message_browser.update_events(events)
