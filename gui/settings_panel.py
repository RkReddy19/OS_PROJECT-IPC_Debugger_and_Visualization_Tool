"""
Settings Panel — application preferences and configuration.
"""

import tkinter as tk
from tkinter import ttk

from utils.constants import COLORS


class SettingsPanel:
    """Application settings panel with runtime-adjustable parameters."""

    def __init__(self, parent: tk.Widget, on_settings_changed=None):
        self.parent = parent
        self._on_change = on_settings_changed

        # ── Animation Settings ──
        card1 = tk.Frame(parent, bg=COLORS["panel_bg"], padx=16, pady=12)
        card1.pack(fill="x", padx=8, pady=(8, 4))

        tk.Label(card1, text="\U0001f3ac Animation Settings",
                 font=("Segoe UI", 12, "bold"),
                 bg=COLORS["panel_bg"], fg=COLORS["accent"]).pack(anchor="w")
        tk.Frame(card1, bg=COLORS["card_bg"], height=1).pack(fill="x", pady=(6, 10))

        fields1 = tk.Frame(card1, bg=COLORS["panel_bg"])
        fields1.pack(fill="x")

        # Animation FPS
        tk.Label(fields1, text="Animation FPS:", font=("Segoe UI", 10),
                 bg=COLORS["panel_bg"], fg=COLORS["text_muted"]).grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=3)
        self.fps_var = tk.IntVar(value=60)
        fps_spin = tk.Spinbox(fields1, from_=15, to=120, width=6,
                               textvariable=self.fps_var,
                               font=("Segoe UI", 10), bg=COLORS["card_bg"],
                               fg=COLORS["text"], buttonbackground=COLORS["card_bg"],
                               relief="flat")
        fps_spin.grid(row=0, column=1, sticky="w", pady=3)

        # Refresh Interval
        tk.Label(fields1, text="UI Refresh (ms):", font=("Segoe UI", 10),
                 bg=COLORS["panel_bg"], fg=COLORS["text_muted"]).grid(
            row=1, column=0, sticky="w", padx=(0, 8), pady=3)
        self.refresh_var = tk.IntVar(value=2000)
        refresh_spin = tk.Spinbox(fields1, from_=500, to=10000, increment=500,
                                   width=6, textvariable=self.refresh_var,
                                   font=("Segoe UI", 10), bg=COLORS["card_bg"],
                                   fg=COLORS["text"], buttonbackground=COLORS["card_bg"],
                                   relief="flat")
        refresh_spin.grid(row=1, column=1, sticky="w", pady=3)

        # Lerp Speed
        tk.Label(fields1, text="Lerp Speed:", font=("Segoe UI", 10),
                 bg=COLORS["panel_bg"], fg=COLORS["text_muted"]).grid(
            row=2, column=0, sticky="w", padx=(0, 8), pady=3)
        self.lerp_var = tk.DoubleVar(value=0.08)
        lerp_scale = tk.Scale(fields1, from_=0.01, to=0.3, resolution=0.01,
                               orient="horizontal", variable=self.lerp_var,
                               font=("Segoe UI", 8), bg=COLORS["panel_bg"],
                               fg=COLORS["text"], highlightthickness=0,
                               troughcolor=COLORS["card_bg"],
                               activebackground=COLORS["accent"],
                               length=150)
        lerp_scale.grid(row=2, column=1, sticky="w", pady=3)

        # ── Analysis Settings ──
        card2 = tk.Frame(parent, bg=COLORS["panel_bg"], padx=16, pady=12)
        card2.pack(fill="x", padx=8, pady=4)

        tk.Label(card2, text="\U0001f50d Analysis Settings",
                 font=("Segoe UI", 12, "bold"),
                 bg=COLORS["panel_bg"], fg=COLORS["accent"]).pack(anchor="w")
        tk.Frame(card2, bg=COLORS["card_bg"], height=1).pack(fill="x", pady=(6, 10))

        fields2 = tk.Frame(card2, bg=COLORS["panel_bg"])
        fields2.pack(fill="x")

        # Auto-deadlock
        self.auto_deadlock_var = tk.BooleanVar(value=False)
        tk.Checkbutton(fields2, text="Auto Deadlock Detection",
                        variable=self.auto_deadlock_var,
                        bg=COLORS["panel_bg"], fg=COLORS["text"],
                        selectcolor=COLORS["card_bg"],
                        activebackground=COLORS["panel_bg"],
                        activeforeground=COLORS["text"],
                        font=("Segoe UI", 10)).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=3)

        # Auto-bottleneck
        self.auto_bottleneck_var = tk.BooleanVar(value=False)
        tk.Checkbutton(fields2, text="Auto Bottleneck Analysis",
                        variable=self.auto_bottleneck_var,
                        bg=COLORS["panel_bg"], fg=COLORS["text"],
                        selectcolor=COLORS["card_bg"],
                        activebackground=COLORS["panel_bg"],
                        activeforeground=COLORS["text"],
                        font=("Segoe UI", 10)).grid(
            row=1, column=0, columnspan=2, sticky="w", pady=3)

        # Race detection time window
        tk.Label(fields2, text="Race Window (ms):", font=("Segoe UI", 10),
                 bg=COLORS["panel_bg"], fg=COLORS["text_muted"]).grid(
            row=2, column=0, sticky="w", padx=(0, 8), pady=3)
        self.race_window_var = tk.IntVar(value=50)
        race_spin = tk.Spinbox(fields2, from_=10, to=500, increment=10,
                                width=6, textvariable=self.race_window_var,
                                font=("Segoe UI", 10), bg=COLORS["card_bg"],
                                fg=COLORS["text"], buttonbackground=COLORS["card_bg"],
                                relief="flat")
        race_spin.grid(row=2, column=1, sticky="w", pady=3)

        # ── Logging Settings ──
        card3 = tk.Frame(parent, bg=COLORS["panel_bg"], padx=16, pady=12)
        card3.pack(fill="x", padx=8, pady=4)

        tk.Label(card3, text="\U0001f4dd Logging Settings",
                 font=("Segoe UI", 12, "bold"),
                 bg=COLORS["panel_bg"], fg=COLORS["accent"]).pack(anchor="w")
        tk.Frame(card3, bg=COLORS["card_bg"], height=1).pack(fill="x", pady=(6, 10))

        fields3 = tk.Frame(card3, bg=COLORS["panel_bg"])
        fields3.pack(fill="x")

        tk.Label(fields3, text="Log Level:", font=("Segoe UI", 10),
                 bg=COLORS["panel_bg"], fg=COLORS["text_muted"]).grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=3)
        self.log_level_var = tk.StringVar(value="INFO")
        log_combo = ttk.Combobox(fields3, textvariable=self.log_level_var,
                                  values=["DEBUG", "INFO", "WARNING", "ERROR"],
                                  state="readonly", width=12, font=("Segoe UI", 10))
        log_combo.grid(row=0, column=1, sticky="w", pady=3)

        tk.Label(fields3, text="Max Events:", font=("Segoe UI", 10),
                 bg=COLORS["panel_bg"], fg=COLORS["text_muted"]).grid(
            row=1, column=0, sticky="w", padx=(0, 8), pady=3)
        self.max_events_var = tk.IntVar(value=10000)
        events_spin = tk.Spinbox(fields3, from_=1000, to=100000, increment=1000,
                                  width=8, textvariable=self.max_events_var,
                                  font=("Segoe UI", 10), bg=COLORS["card_bg"],
                                  fg=COLORS["text"], buttonbackground=COLORS["card_bg"],
                                  relief="flat")
        events_spin.grid(row=1, column=1, sticky="w", pady=3)

        # ── About Section ──
        card4 = tk.Frame(parent, bg=COLORS["panel_bg"], padx=16, pady=12)
        card4.pack(fill="x", padx=8, pady=(4, 8))

        tk.Label(card4, text="\U0001f4a1 About",
                 font=("Segoe UI", 12, "bold"),
                 bg=COLORS["panel_bg"], fg=COLORS["accent"]).pack(anchor="w")
        tk.Frame(card4, bg=COLORS["card_bg"], height=1).pack(fill="x", pady=(6, 10))

        about_text = (
            "IPC Debugger & Visualization Tool\n"
            "Version 2.0\n\n"
            "An interactive debugging and analysis platform\n"
            "for inter-process communication systems.\n\n"
            "Supports: Pipes, Message Queues, Shared Memory\n"
            "Detects: Deadlocks, Bottlenecks, Race Conditions\n\n"
            "Keyboard Shortcuts:\n"
            "  Ctrl+S  Start Simulation\n"
            "  Ctrl+P  Pause/Resume\n"
            "  Ctrl+R  Reset All\n"
            "  Ctrl+D  Deadlock Detection\n"
            "  Ctrl+B  Bottleneck Analysis"
        )
        tk.Label(card4, text=about_text, font=("Segoe UI", 9),
                 bg=COLORS["panel_bg"], fg=COLORS["text_muted"],
                 justify="left").pack(anchor="w")

    def get_settings(self) -> dict:
        """Return current settings as a dictionary."""
        return {
            "fps": self.fps_var.get(),
            "refresh_ms": self.refresh_var.get(),
            "lerp_speed": self.lerp_var.get(),
            "auto_deadlock": self.auto_deadlock_var.get(),
            "auto_bottleneck": self.auto_bottleneck_var.get(),
            "race_window_ms": self.race_window_var.get(),
            "log_level": self.log_level_var.get(),
            "max_events": self.max_events_var.get(),
        }
