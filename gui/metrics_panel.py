"""
Metrics Panel — Matplotlib bar charts for channel performance.
Updated with modern dark theme colors and queue depth history chart.
"""

import tkinter as tk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from typing import List, Optional

from utils.models import ChannelMetrics
from utils.constants import COLORS


class MetricsPanel:
    """Matplotlib-based performance metrics dashboard."""

    def __init__(self, parent: tk.Widget):
        self.parent = parent
        self.fig = Figure(figsize=(8, 2.5), dpi=100, facecolor=COLORS["bg"])
        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.widget = self.canvas.get_tk_widget()
        self._visible = False

    def show(self):
        if not self._visible:
            self.widget.pack(fill=tk.BOTH, expand=False, padx=4, pady=4)
            self._visible = True

    def hide(self):
        if self._visible:
            self.widget.pack_forget()
            self._visible = False

    def update_metrics(self, metrics: List[ChannelMetrics],
                       channels: Optional[list] = None) -> None:
        """Update all metric charts.

        Args:
            metrics: List of ChannelMetrics dataclass instances.
            channels: Optional list of IPCChannel objects (used for depth_history).
        """
        self.fig.clear()
        self.fig.patch.set_facecolor(COLORS["bg"])

        if not metrics:
            ax = self.fig.add_subplot(111)
            ax.set_facecolor(COLORS["bg"])
            ax.text(0.5, 0.5, "No metrics available.",
                    ha='center', va='center', fontsize=12,
                    color=COLORS["text_muted"], transform=ax.transAxes)
            ax.axis('off')
            self.canvas.draw()
            return

        names = [m.name for m in metrics]
        x_pos = range(len(names))

        # Determine layout: 2x2 if we have depth history, else 1x3
        has_depth = False
        if channels:
            from ipc.queue_channel import QueueChannel
            has_depth = any(
                isinstance(ch, QueueChannel) and ch.depth_history
                for ch in channels
            )

        if has_depth:
            ax1 = self.fig.add_subplot(221)
            ax2 = self.fig.add_subplot(222)
            ax3 = self.fig.add_subplot(223)
            ax4 = self.fig.add_subplot(224)
        else:
            ax1 = self.fig.add_subplot(131)
            ax2 = self.fig.add_subplot(132)
            ax3 = self.fig.add_subplot(133)
            ax4 = None

        # ── Subplot 1: Avg Latency ──
        ax1.set_facecolor(COLORS["panel_bg"])
        ax1.bar(x_pos, [m.avg_latency for m in metrics],
                color=COLORS["pipe"], alpha=0.85, edgecolor=COLORS["pipe"], linewidth=0.5)
        ax1.set_title("Avg Latency (s)", color=COLORS["text"], fontsize=9)
        ax1.set_xticks(list(x_pos))
        ax1.set_xticklabels(names, rotation=45, ha='right', fontsize=7, color=COLORS["text_muted"])
        ax1.tick_params(colors=COLORS["text_dim"])
        for spine in ax1.spines.values():
            spine.set_color(COLORS["text_dim"])

        # ── Subplot 2: Throughput ──
        ax2.set_facecolor(COLORS["panel_bg"])
        ax2.bar(x_pos, [m.throughput for m in metrics],
                color=COLORS["queue"], alpha=0.85, edgecolor=COLORS["queue"], linewidth=0.5)
        ax2.set_title("Throughput (msg/s)", color=COLORS["text"], fontsize=9)
        ax2.set_xticks(list(x_pos))
        ax2.set_xticklabels(names, rotation=45, ha='right', fontsize=7, color=COLORS["text_muted"])
        ax2.tick_params(colors=COLORS["text_dim"])
        for spine in ax2.spines.values():
            spine.set_color(COLORS["text_dim"])

        # ── Subplot 3: Queue Depth (current vs peak) ──
        ax3.set_facecolor(COLORS["panel_bg"])
        bar_w = 0.35
        x_list = list(x_pos)
        ax3.bar([xi - bar_w/2 for xi in x_list], [m.queue_depth for m in metrics],
                width=bar_w, color=COLORS["shared_memory"], alpha=0.85, label="Current")
        ax3.bar([xi + bar_w/2 for xi in x_list], [m.peak_depth for m in metrics],
                width=bar_w, color=COLORS["accent_err"], alpha=0.6, label="Peak")
        ax3.set_title("Queue Depth", color=COLORS["text"], fontsize=9)
        ax3.set_xticks(x_list)
        ax3.set_xticklabels(names, rotation=45, ha='right', fontsize=7, color=COLORS["text_muted"])
        ax3.tick_params(colors=COLORS["text_dim"])
        ax3.legend(fontsize=7, facecolor=COLORS["panel_bg"],
                   edgecolor=COLORS["text_dim"], labelcolor=COLORS["text"])
        for spine in ax3.spines.values():
            spine.set_color(COLORS["text_dim"])

        # ── Subplot 4: Queue Depth Over Time ──
        if ax4 is not None and channels:
            from ipc.queue_channel import QueueChannel
            ax4.set_facecolor(COLORS["panel_bg"])
            plotted = False
            ch_colors = [COLORS["pipe"], COLORS["queue"], COLORS["shared_memory"],
                         COLORS["accent"], COLORS["accent_warn"]]
            color_idx = 0
            for ch in channels:
                if isinstance(ch, QueueChannel) and ch.depth_history:
                    times, depths = zip(*ch.depth_history)
                    # Normalize times to start from 0
                    t0 = times[0]
                    rel_times = [t - t0 for t in times]
                    ax4.plot(rel_times, depths,
                             color=ch_colors[color_idx % len(ch_colors)],
                             linewidth=1.5, alpha=0.9, label=ch.name)
                    color_idx += 1
                    plotted = True
            if plotted:
                ax4.set_title("Queue Depth Over Time", color=COLORS["text"], fontsize=9)
                ax4.set_xlabel("Time (s)", fontsize=7, color=COLORS["text_muted"])
                ax4.set_ylabel("Depth", fontsize=7, color=COLORS["text_muted"])
                ax4.tick_params(colors=COLORS["text_dim"], labelsize=7)
                ax4.legend(fontsize=6, facecolor=COLORS["panel_bg"],
                           edgecolor=COLORS["text_dim"], labelcolor=COLORS["text"])
                for spine in ax4.spines.values():
                    spine.set_color(COLORS["text_dim"])
            else:
                ax4.axis('off')

        self.fig.tight_layout()
        self.canvas.draw()

    def save_png(self, filepath: str) -> None:
        self.fig.savefig(filepath, facecolor=COLORS["bg"],
                         edgecolor='none', dpi=150, bbox_inches='tight')
