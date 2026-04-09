"""
Tooltip Widget — hover tooltips for Tkinter widgets.
"""

import tkinter as tk
from utils.constants import COLORS


class ToolTip:
    """Hover tooltip for any Tkinter widget."""

    def __init__(self, widget, text, delay=400):
        self.widget = widget
        self.text = text
        self.delay = delay
        self._tip = None
        self._id = None
        widget.bind("<Enter>", self._schedule)
        widget.bind("<Leave>", self._hide)

    def _schedule(self, event=None):
        self._id = self.widget.after(self.delay, self._show)

    def _show(self):
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self._tip = tk.Toplevel(self.widget)
        self._tip.wm_overrideredirect(True)
        self._tip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            self._tip, text=self.text, justify="left",
            bg="#334155", fg="#e2e8f0", relief="solid", borderwidth=1,
            font=("Segoe UI", 9), padx=8, pady=4,
        )
        label.pack()

    def _hide(self, event=None):
        if self._id:
            self.widget.after_cancel(self._id)
            self._id = None
        if self._tip:
            self._tip.destroy()
            self._tip = None
