"""
Log Panel — color-coded scrolling event log with icons and timestamps.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime

from utils.models import LogEvent
from utils.constants import COLORS, LOG_TAG_COLORS, LOG_ICONS


class LogPanel:
    """Scrollable color-coded event log widget with emoji icons."""

    def __init__(self, parent: tk.Widget):
        self.parent = parent

        header = tk.Frame(parent, bg=COLORS["panel_bg"])
        header.pack(fill="x", padx=8, pady=(6, 2))
        tk.Label(header, text="Event Log", font=("Segoe UI", 11, "bold"),
                 bg=COLORS["panel_bg"], fg=COLORS["accent"]).pack(side="left")
        clear_btn = tk.Button(
            header, text="  Clear  ", font=("Segoe UI", 9, "bold"),
            bg="#475569", fg=COLORS["text"],
            activebackground="#64748b",
            activeforeground=COLORS["text"], relief="flat",
            padx=12, pady=3, cursor="hand2", command=self.clear, bd=0,
        )
        clear_btn.bind("<Enter>", lambda e: clear_btn.config(bg="#64748b"))
        clear_btn.bind("<Leave>", lambda e: clear_btn.config(bg="#475569"))
        clear_btn.pack(side="right")

        self.text = scrolledtext.ScrolledText(
            parent, height=8, bg=COLORS["bg_darker"], fg=COLORS["text"],
            font=("Consolas", 9), insertbackground=COLORS["text"],
            state="disabled", wrap="word", relief="flat",
            selectbackground=COLORS["accent"], selectforeground="#fff",
        )
        self.text.pack(fill=tk.BOTH, expand=True, padx=8, pady=(2, 6))

        for tag, color in LOG_TAG_COLORS.items():
            kwargs = {"foreground": color}
            if tag in ("DEADLOCK", "RACE"):
                kwargs["font"] = ("Consolas", 10, "bold")
            elif tag == "BOTTLENECK":
                kwargs["font"] = ("Consolas", 9, "bold")
            self.text.tag_config(tag, **kwargs)
        self.text.tag_config("TIMESTAMP", foreground=COLORS["text_dim"],
                             font=("Consolas", 8))

    def append(self, event: LogEvent):
        icon = LOG_ICONS.get(event.action, "\u2022")
        ts = datetime.now().strftime("%H:%M:%S")
        self.text.configure(state="normal")
        self.text.insert(tk.END, f"  [{ts}] ", "TIMESTAMP")
        self.text.insert(tk.END, f"{icon} {str(event)}\n", event.action)
        self.text.see(tk.END)
        self.text.configure(state="disabled")

    def clear(self):
        self.text.configure(state="normal")
        self.text.delete("1.0", tk.END)
        self.text.configure(state="disabled")

    def get_all_text(self) -> str:
        return self.text.get("1.0", tk.END)
