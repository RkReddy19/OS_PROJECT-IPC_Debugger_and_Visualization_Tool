"""
Message Browser — Treeview-based message history with filtering and search.
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Optional

from utils.models import LogEvent
from utils.constants import COLORS, LOG_TAG_COLORS


class MessageBrowser:
    """Filterable, searchable message history panel."""

    def __init__(self, parent: tk.Widget):
        self.parent = parent
        self._events: List[LogEvent] = []

        # ── Header with filters ──
        header = tk.Frame(parent, bg=COLORS["panel_bg"])
        header.pack(fill="x", padx=8, pady=(8, 4))

        tk.Label(header, text="\U0001f4e8 Message Browser",
                 font=("Segoe UI", 11, "bold"),
                 bg=COLORS["panel_bg"], fg=COLORS["accent"]).pack(side="left")

        # Search
        search_frame = tk.Frame(header, bg=COLORS["panel_bg"])
        search_frame.pack(side="right")

        tk.Label(search_frame, text="\U0001f50d", font=("Segoe UI", 10),
                 bg=COLORS["panel_bg"], fg=COLORS["text_muted"]).pack(side="left")
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *a: self._apply_filters())
        self._search_entry = tk.Entry(
            search_frame, textvariable=self._search_var,
            font=("Segoe UI", 9), width=16,
            bg=COLORS["card_bg"], fg=COLORS["text"],
            insertbackground=COLORS["text"], relief="flat",
            highlightthickness=1, highlightcolor=COLORS["accent"],
            highlightbackground=COLORS["text_dim"])
        self._search_entry.pack(side="left", padx=4)

        # Filter row
        filter_frame = tk.Frame(parent, bg=COLORS["bg"])
        filter_frame.pack(fill="x", padx=8, pady=2)

        tk.Label(filter_frame, text="Action:", font=("Segoe UI", 9),
                 bg=COLORS["bg"], fg=COLORS["text_muted"]).pack(side="left")
        self._action_var = tk.StringVar(value="All")
        action_combo = ttk.Combobox(
            filter_frame, textvariable=self._action_var,
            values=["All", "SEND", "RECEIVE", "LOCK_REQUEST",
                    "LOCK_ACQUIRE", "LOCK_RELEASE", "DEADLOCK",
                    "BOTTLENECK", "RACE", "INFO", "WARNING"],
            state="readonly", width=14, font=("Segoe UI", 9))
        action_combo.pack(side="left", padx=4)
        action_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())

        tk.Label(filter_frame, text="Process:", font=("Segoe UI", 9),
                 bg=COLORS["bg"], fg=COLORS["text_muted"]).pack(side="left", padx=(12, 0))
        self._pid_var = tk.StringVar(value="All")
        self._pid_combo = ttk.Combobox(
            filter_frame, textvariable=self._pid_var,
            values=["All"], state="readonly", width=14, font=("Segoe UI", 9))
        self._pid_combo.pack(side="left", padx=4)
        self._pid_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())

        # Count label
        self._count_label = tk.Label(
            filter_frame, text="0 events",
            font=("Segoe UI", 9), bg=COLORS["bg"], fg=COLORS["text_dim"])
        self._count_label.pack(side="right", padx=8)

        # ── Treeview ──
        tree_frame = tk.Frame(parent, bg=COLORS["bg"])
        tree_frame.pack(fill="both", expand=True, padx=8, pady=(2, 8))

        columns = ("time", "source", "dest", "action", "size", "channel", "details")
        self._tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings",
            height=12, selectmode="browse")

        # Column configuration
        col_config = [
            ("time",    "Time",    70,  "center"),
            ("source",  "Source",  80,  "w"),
            ("dest",    "Dest",    80,  "w"),
            ("action",  "Action",  90,  "center"),
            ("size",    "Bytes",   55,  "center"),
            ("channel", "Channel", 100, "w"),
            ("details", "Details", 200, "w"),
        ]
        for col_id, heading, width, anchor in col_config:
            self._tree.heading(col_id, text=heading,
                               command=lambda c=col_id: self._sort_by(c))
            self._tree.column(col_id, width=width, anchor=anchor, minwidth=40)

        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical",
                                   command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)

        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Style treeview for dark theme
        style = ttk.Style()
        style.configure("Treeview",
                        background=COLORS["bg"],
                        foreground=COLORS["text"],
                        fieldbackground=COLORS["bg"],
                        font=("Consolas", 9),
                        rowheight=22)
        style.configure("Treeview.Heading",
                        background=COLORS["card_bg"],
                        foreground=COLORS["accent"],
                        font=("Segoe UI", 9, "bold"))
        style.map("Treeview",
                  background=[("selected", COLORS["card_bg"])],
                  foreground=[("selected", COLORS["accent"])])

        # Tag colors for action types
        for action, color in LOG_TAG_COLORS.items():
            self._tree.tag_configure(action, foreground=color)

        self._sort_reverse = False
        self._sort_col = "time"

    def update_events(self, events: List[LogEvent]) -> None:
        """Replace the event list and refresh display."""
        self._events = events

        # Update PID filter list
        pids = sorted(set(e.source_pid for e in events if e.source_pid))
        self._pid_combo["values"] = ["All"] + pids

        self._apply_filters()

    def _apply_filters(self) -> None:
        """Apply action/pid/search filters and repopulate tree."""
        # Clear tree
        for item in self._tree.get_children():
            self._tree.delete(item)

        action_filter = self._action_var.get()
        pid_filter = self._pid_var.get()
        search_text = self._search_var.get().lower()

        filtered = []
        for e in self._events:
            if action_filter != "All" and e.action != action_filter:
                continue
            if pid_filter != "All" and e.source_pid != pid_filter:
                continue
            if search_text:
                searchable = f"{e.source_pid} {e.dest_pid} {e.action} {e.details} {e.channel_name}".lower()
                if search_text not in searchable:
                    continue
            filtered.append(e)

        # Apply sorting
        filtered.sort(
            key=lambda e: getattr(e, self._sort_col, e.timestamp),
            reverse=self._sort_reverse
        )

        # Populate
        for e in filtered:
            values = (
                f"{e.timestamp:.3f}",
                e.source_pid,
                e.dest_pid,
                e.action,
                str(e.data_size) if e.data_size > 0 else "",
                e.channel_name,
                e.details[:80],
            )
            tag = e.action if e.action in LOG_TAG_COLORS else ""
            self._tree.insert("", "end", values=values, tags=(tag,))

        self._count_label.config(text=f"{len(filtered)} events")

    def _sort_by(self, col: str) -> None:
        """Sort treeview by column."""
        if self._sort_col == col:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_col = col
            self._sort_reverse = False
        self._apply_filters()

    def clear(self) -> None:
        """Clear all events."""
        self._events = []
        for item in self._tree.get_children():
            self._tree.delete(item)
        self._count_label.config(text="0 events")
