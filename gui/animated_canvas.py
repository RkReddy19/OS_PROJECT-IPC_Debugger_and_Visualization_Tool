"""
Animated Canvas — 60fps Tkinter Canvas for IPC topology visualization.
Smooth position interpolation, pulse animations, deadlock glow effects.
"""

import math
import tkinter as tk
import networkx as nx
from typing import Dict, List, Tuple, Set, Optional

from utils.constants import (
    COLORS, EDGE_STYLES, ANIMATION_FRAME_MS, LERP_SPEED,
    NODE_RADIUS, NODE_RADIUS_DEADLOCK, NODE_OUTLINE_WIDTH,
    GLOW_RINGS, GLOW_BASE_OFFSET, GLOW_RING_STEP,
)


class _NodeState:
    """Internal state for an animated node."""
    __slots__ = ['cx', 'cy', 'tx', 'ty', 'state']

    def __init__(self, x: float, y: float):
        self.cx = x    # current x
        self.cy = y    # current y
        self.tx = x    # target x
        self.ty = y    # target y
        self.state = "idle"


class AnimatedCanvas:
    """Custom Tkinter Canvas with smooth animations for the IPC topology.

    Features:
        - Nodes as colored circles with state-based fill
        - Edges as styled arrows (solid/dashed/dotted by channel type)
        - Smooth position interpolation when topology changes
        - Pulse animation on active message transfers
        - Glow rings on deadlocked nodes
        - Legend overlay
    """

    def __init__(self, parent: tk.Widget):
        self.canvas = tk.Canvas(
            parent, bg=COLORS["bg"], highlightthickness=0,
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", self._on_resize)

        self._nodes: Dict[str, _NodeState] = {}
        self._edges: List[dict] = []
        self._deadlock_nodes: Set[str] = set()
        self._deadlock_edges: Set[Tuple[str, str]] = set()
        self._pulse_edges: Dict[Tuple[str, str], float] = {}

        self._animating = False
        self._width = 800
        self._height = 500
        self._needs_layout = False
        self._layout_cache = None
        self._topology_hash = None

    # ─── Public API ───

    def update_topology(self, process_ids: List[str],
                        connections: List[dict],
                        process_states: Dict[str, str]):
        """Rebuild the graph from the current topology."""
        # Build a NetworkX graph for layout computation
        G = nx.DiGraph()
        for pid in process_ids:
            G.add_node(pid)
        for conn in connections:
            G.add_edge(conn["source"], conn["dest"])

        # Compute target positions (cached by topology hash)
        if len(G.nodes) > 0:
            topo_hash = (frozenset(G.nodes), frozenset(G.edges))
            if topo_hash != self._topology_hash or self._layout_cache is None:
                try:
                    pos = nx.spring_layout(G, k=2.5, iterations=50, seed=42)
                except Exception:
                    pos = nx.circular_layout(G)
                self._layout_cache = pos
                self._topology_hash = topo_hash
            else:
                pos = self._layout_cache

            margin = 80
            w = max(self._width, 400)
            h = max(self._height, 300)
            for pid, (x, y) in pos.items():
                tx = margin + (x + 1) * (w - 2 * margin) / 2
                ty = margin + (y + 1) * (h - 2 * margin) / 2
                if pid not in self._nodes:
                    self._nodes[pid] = _NodeState(tx, ty)
                else:
                    self._nodes[pid].tx = tx
                    self._nodes[pid].ty = ty

        # Update states
        for pid in process_ids:
            if pid in self._nodes:
                self._nodes[pid].state = process_states.get(pid, "idle")

        # Remove stale nodes
        current = set(process_ids)
        for pid in list(self._nodes):
            if pid not in current:
                del self._nodes[pid]

        self._edges = connections

        if not self._animating:
            self._start_animation()

    def set_deadlock_info(self, nodes: List[str],
                          edges: List[Tuple[str, str]]):
        self._deadlock_nodes = set(nodes)
        self._deadlock_edges = set(edges)

    def clear_deadlock_info(self):
        self._deadlock_nodes.clear()
        self._deadlock_edges.clear()

    def pulse_edge(self, source: str, dest: str):
        """Trigger a message-transfer pulse animation on an edge."""
        self._pulse_edges[(source, dest)] = 0.0

    def stop_animation(self):
        self._animating = False

    # ─── Animation Loop ───

    def _start_animation(self):
        self._animating = True
        self._animate()

    def _animate(self):
        if not self._animating:
            return
        self._update_positions()
        self._update_pulses()
        self._draw_frame()
        self.canvas.after(ANIMATION_FRAME_MS, self._animate)

    def _update_positions(self):
        for node in self._nodes.values():
            node.cx += (node.tx - node.cx) * LERP_SPEED
            node.cy += (node.ty - node.cy) * LERP_SPEED

    def _update_pulses(self):
        done = []
        for key in self._pulse_edges:
            self._pulse_edges[key] += 0.03
            if self._pulse_edges[key] >= 1.0:
                done.append(key)
        for key in done:
            del self._pulse_edges[key]

    def _on_resize(self, event):
        self._width = event.width
        self._height = event.height

    # ─── Rendering ───

    def _draw_frame(self):
        self.canvas.delete("all")

        if not self._nodes:
            self.canvas.create_text(
                self._width // 2, self._height // 2,
                text="No processes added yet.\nUse the Control Panel to add processes.",
                fill=COLORS["text"], font=("Segoe UI", 14, "italic"),
                justify="center",
            )
            return

        self._draw_edges()
        self._draw_pulses()
        self._draw_nodes()
        self._draw_legend()

    def _draw_edges(self):
        for conn in self._edges:
            src = self._nodes.get(conn["source"])
            dst = self._nodes.get(conn["dest"])
            if not src or not dst:
                continue

            edge_key = (conn["source"], conn["dest"])
            is_dl = edge_key in self._deadlock_edges
            ch_type = conn.get("channel_type", "pipe")

            if is_dl:
                color = COLORS["edge_deadlock"]
                width = 3.5
                dash = ()
            else:
                color = COLORS.get(ch_type, COLORS["edge_active"])
                width = 2.0
                dash = EDGE_STYLES.get(ch_type, ())

            # Offset for arrowhead (don't overlap nodes)
            dx = dst.cx - src.cx
            dy = dst.cy - src.cy
            dist = math.hypot(dx, dy) or 1
            r = NODE_RADIUS + 4
            ex = dst.cx - (dx / dist) * r
            ey = dst.cy - (dy / dist) * r
            sx = src.cx + (dx / dist) * (NODE_RADIUS + 2)
            sy = src.cy + (dy / dist) * (NODE_RADIUS + 2)

            self.canvas.create_line(
                sx, sy, ex, ey,
                fill=color, width=width, dash=dash if dash else None,
                arrow=tk.LAST, arrowshape=(12, 15, 5),
                smooth=True,
            )

            # Edge label at midpoint
            mx = (src.cx + dst.cx) / 2
            my = (src.cy + dst.cy) / 2 - 14
            label = f"{conn.get('channel_name', '')}\n({ch_type})"
            self.canvas.create_text(
                mx, my, text=label, fill=COLORS["text"],
                font=("Segoe UI", 7), justify="center",
            )

    def _draw_pulses(self):
        for (src_id, dst_id), phase in self._pulse_edges.items():
            src = self._nodes.get(src_id)
            dst = self._nodes.get(dst_id)
            if not src or not dst:
                continue
            px = src.cx + (dst.cx - src.cx) * phase
            py = src.cy + (dst.cy - src.cy) * phase
            r = 5
            self.canvas.create_oval(
                px - r, py - r, px + r, py + r,
                fill="#f1c40f", outline="#f39c12", width=1,
            )

    def _draw_nodes(self):
        for pid, node in self._nodes.items():
            is_dl = pid in self._deadlock_nodes
            state = node.state

            if is_dl:
                color = COLORS["deadlocked"]
                radius = NODE_RADIUS_DEADLOCK
                # Glow rings
                for i in range(GLOW_RINGS):
                    gr = radius + GLOW_BASE_OFFSET + i * GLOW_RING_STEP
                    alpha_colors = ["#e74c3c", "#c0392b", "#a93226"]
                    self.canvas.create_oval(
                        node.cx - gr, node.cy - gr,
                        node.cx + gr, node.cy + gr,
                        outline=alpha_colors[i], width=1, dash=(3, 3),
                    )
            else:
                color = COLORS.get(state, COLORS["idle"])
                radius = NODE_RADIUS

            # Node body
            self.canvas.create_oval(
                node.cx - radius, node.cy - radius,
                node.cx + radius, node.cy + radius,
                fill=color, outline="#ffffff", width=NODE_OUTLINE_WIDTH,
            )

            # Node label
            self.canvas.create_text(
                node.cx, node.cy,
                text=pid, fill="#ffffff",
                font=("Segoe UI", 9, "bold"),
            )

    def _draw_legend(self):
        x, y = 15, 15
        items = [
            ("Running", COLORS["running"]),
            ("Paused", COLORS["paused"]),
            ("Deadlocked", COLORS["deadlocked"]),
            ("Idle/Stopped", COLORS["idle"]),
        ]
        # Background box
        bw, bh = 120, len(items) * 22 + 10
        self.canvas.create_rectangle(
            x - 5, y - 5, x + bw, y + bh,
            fill=COLORS["panel_bg"], outline=COLORS["text"], width=1,
            stipple="gray50",
        )
        for label, color in items:
            self.canvas.create_rectangle(x, y, x + 14, y + 14, fill=color, outline="")
            self.canvas.create_text(
                x + 20, y + 7, text=label, fill=COLORS["text"],
                font=("Segoe UI", 8), anchor="w",
            )
            y += 22
