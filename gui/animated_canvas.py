"""
Animated Canvas — 60fps Tkinter Canvas for IPC topology visualization.
Smooth position interpolation, pulse animations, deadlock glow effects.

Optimizations:
- Incremental rendering with dirty flags (avoids full redraw every frame)
- Thread-safe node state via locking
- Interactive node dragging
- Hover tooltips showing process stats
- Auto-triggered message pulse animations
- Enhanced legend with channel type line styles
"""

import math
import threading
import tkinter as tk
import networkx as nx
from typing import Dict, List, Tuple, Set, Optional

from utils.constants import (
    COLORS, EDGE_STYLES, ANIMATION_FRAME_MS, LERP_SPEED,
    NODE_RADIUS, NODE_RADIUS_DEADLOCK, NODE_OUTLINE_WIDTH,
    GLOW_RINGS, GLOW_BASE_OFFSET, GLOW_RING_STEP, GUI_CONFIG,
)


class _NodeState:
    """Thread-safe internal state for an animated node."""
    __slots__ = ['cx', 'cy', 'tx', 'ty', 'state', 'messages_sent',
                 'messages_received', 'behavior', '_lock', '_last_state']

    def __init__(self, x: float, y: float) -> None:
        self.cx: float = x    # current x
        self.cy: float = y    # current y
        self.tx: float = x    # target x
        self.ty: float = y    # target y
        self.state: str = "idle"
        self.messages_sent: int = 0
        self.messages_received: int = 0
        self.behavior: str = ""
        self._lock = threading.Lock()
        self._last_state: str = ""

    def update_position(self, tx: float, ty: float) -> None:
        """Thread-safe target position update."""
        with self._lock:
            self.tx = tx
            self.ty = ty

    def update_state(self, state: str, msgs_sent: int = -1,
                     msgs_recv: int = -1, behavior: str = "") -> None:
        """Thread-safe state + stats update."""
        with self._lock:
            self.state = state
            if msgs_sent >= 0:
                self.messages_sent = msgs_sent
            if msgs_recv >= 0:
                self.messages_received = msgs_recv
            if behavior:
                self.behavior = behavior

    def get_snapshot(self) -> dict:
        """Thread-safe snapshot of all state."""
        with self._lock:
            return {
                "cx": self.cx, "cy": self.cy,
                "tx": self.tx, "ty": self.ty,
                "state": self.state,
                "messages_sent": self.messages_sent,
                "messages_received": self.messages_received,
                "behavior": self.behavior,
            }

    def interpolate(self) -> bool:
        """Move current position toward target. Returns True if moved."""
        with self._lock:
            dx = self.tx - self.cx
            dy = self.ty - self.cy
            if abs(dx) < 0.5 and abs(dy) < 0.5:
                return False
            self.cx += dx * LERP_SPEED
            self.cy += dy * LERP_SPEED
            return True

    def state_changed(self) -> bool:
        """Check if the state has changed since last render."""
        with self._lock:
            changed = self.state != self._last_state
            self._last_state = self.state
            return changed


class AnimatedCanvas:
    """Custom Tkinter Canvas with optimized incremental rendering.

    Features:
        - Nodes as colored circles with state-based fill
        - Edges as styled arrows (solid/dashed/dotted by channel type)
        - Smooth position interpolation when topology changes
        - Pulse animation on active message transfers
        - Glow rings on deadlocked nodes
        - Interactive node dragging
        - Hover tooltips
        - Legend overlay
        - Dirty-flag rendering: only redraws what changed
    """

    def __init__(self, parent: tk.Widget) -> None:
        self.canvas = tk.Canvas(
            parent, bg=COLORS["bg"], highlightthickness=0,
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", self._on_resize)

        # Node dragging
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

        # Hover tooltip
        self.canvas.bind("<Motion>", self._on_motion)

        self._nodes: Dict[str, _NodeState] = {}
        self._edges: List[dict] = []
        self._deadlock_nodes: Set[str] = set()
        self._deadlock_edges: Set[Tuple[str, str]] = set()
        self._pulse_edges: Dict[Tuple[str, str], float] = {}

        self._animating: bool = False
        self._width: int = 800
        self._height: int = 500
        self._needs_layout: bool = False
        self._layout_cache = None
        self._topology_hash = None

        # Dirty flags for incremental rendering
        self._dirty_topology: bool = True
        self._dirty_deadlock: bool = False
        self._frame_count: int = 0

        # Canvas object ID cache for incremental updates
        self._obj_cache: Dict[str, dict] = {}

        # Drag state
        self._drag_pid: Optional[str] = None
        self._drag_offset: Tuple[float, float] = (0, 0)

        # Tooltip state
        self._tooltip_win: Optional[tk.Toplevel] = None
        self._hover_pid: Optional[str] = None

        # Process stats reference (set by controller)
        self._process_engine = None

    # ─── Public API ───

    def update_topology(self, process_ids: List[str],
                        connections: List[dict],
                        process_states: Dict[str, str]) -> None:
        """Rebuild the graph from the current topology."""
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
                self._dirty_topology = True
            else:
                pos = self._layout_cache

            margin = 80
            w = max(self._width, GC_CANVAS["min_width"])
            h = max(self._height, GC_CANVAS["min_height"])
            for pid, (x, y) in pos.items():
                tx = margin + (x + 1) * (w - 2 * margin) / 2
                ty = margin + (y + 1) * (h - 2 * margin) / 2
                if pid not in self._nodes:
                    self._nodes[pid] = _NodeState(tx, ty)
                    self._dirty_topology = True
                else:
                    # Only update target if not being dragged
                    if self._drag_pid != pid:
                        self._nodes[pid].update_position(tx, ty)

        # Update states and process stats
        for pid in process_ids:
            if pid in self._nodes:
                new_state = process_states.get(pid, "idle")
                node = self._nodes[pid]
                # Update stats if engine available
                if self._process_engine:
                    proc = self._process_engine.get_process(pid)
                    if proc:
                        node.update_state(
                            new_state,
                            msgs_sent=proc.messages_sent,
                            msgs_recv=proc.messages_received,
                            behavior=proc.config.behavior,
                        )
                    else:
                        node.update_state(new_state)
                else:
                    node.update_state(new_state)

        # Remove stale nodes
        current = set(process_ids)
        for pid in list(self._nodes):
            if pid not in current:
                del self._nodes[pid]
                self._dirty_topology = True

        self._edges = connections

        if not self._animating:
            self._start_animation()

    def set_deadlock_info(self, nodes: List[str],
                          edges: List[Tuple[str, str]]) -> None:
        self._deadlock_nodes = set(nodes)
        self._deadlock_edges = set(edges)
        self._dirty_deadlock = True

    def clear_deadlock_info(self) -> None:
        if self._deadlock_nodes or self._deadlock_edges:
            self._dirty_deadlock = True
        self._deadlock_nodes.clear()
        self._deadlock_edges.clear()

    def pulse_edge(self, source: str, dest: str) -> None:
        """Trigger a message-transfer pulse animation on an edge."""
        self._pulse_edges[(source, dest)] = 0.0

    def stop_animation(self) -> None:
        self._animating = False

    # ─── Drag Interaction ───

    def _on_press(self, event) -> None:
        """Check if click is on a node and start dragging."""
        for pid, node in self._nodes.items():
            snap = node.get_snapshot()
            dx = event.x - snap["cx"]
            dy = event.y - snap["cy"]
            if math.hypot(dx, dy) <= NODE_RADIUS + 4:
                self._drag_pid = pid
                self._drag_offset = (dx, dy)
                return

    def _on_drag(self, event) -> None:
        """Move dragged node."""
        if self._drag_pid and self._drag_pid in self._nodes:
            node = self._nodes[self._drag_pid]
            new_x = event.x - self._drag_offset[0]
            new_y = event.y - self._drag_offset[1]
            with node._lock:
                node.cx = new_x
                node.cy = new_y
                node.tx = new_x
                node.ty = new_y

    def _on_release(self, event) -> None:
        """Stop dragging."""
        self._drag_pid = None

    # ─── Hover Tooltip ───

    def _on_motion(self, event) -> None:
        """Show tooltip when hovering over a node."""
        hover_pid = None
        for pid, node in self._nodes.items():
            snap = node.get_snapshot()
            dx = event.x - snap["cx"]
            dy = event.y - snap["cy"]
            if math.hypot(dx, dy) <= NODE_RADIUS + 4:
                hover_pid = pid
                break

        if hover_pid != self._hover_pid:
            self._hide_tooltip()
            self._hover_pid = hover_pid
            if hover_pid:
                self._show_tooltip(event, hover_pid)

    def _show_tooltip(self, event, pid: str) -> None:
        """Display a tooltip with process information."""
        node = self._nodes.get(pid)
        if not node:
            return

        snap = node.get_snapshot()

        self._tooltip_win = tk.Toplevel(self.canvas)
        self._tooltip_win.wm_overrideredirect(True)
        x = self.canvas.winfo_rootx() + event.x + 15
        y = self.canvas.winfo_rooty() + event.y + 15
        self._tooltip_win.wm_geometry(f"+{x}+{y}")

        behavior = snap["behavior"] or "unknown"
        info = (
            f"Process: {pid}\n"
            f"State: {snap['state'].upper()}\n"
            f"Behavior: {behavior}\n"
            f"Sent: {snap['messages_sent']}\n"
            f"Received: {snap['messages_received']}"
        )

        label = tk.Label(
            self._tooltip_win, text=info, justify="left",
            bg="#334155", fg="#e2e8f0", relief="solid", borderwidth=1,
            font=GUI_CONFIG["fonts"]["tooltip"], padx=10, pady=6,
        )
        label.pack()

    def _hide_tooltip(self) -> None:
        """Hide the tooltip if visible."""
        if self._tooltip_win:
            self._tooltip_win.destroy()
            self._tooltip_win = None

    # ─── Animation Loop ───

    def _start_animation(self) -> None:
        self._animating = True
        self._animate()

    def _animate(self) -> None:
        if not self._animating:
            return
        self._frame_count += 1

        moved = self._update_positions()
        has_pulses = self._update_pulses()

        # Decide whether to do a full redraw or skip
        needs_redraw = (
            self._dirty_topology
            or self._dirty_deadlock
            or moved
            or has_pulses
            or self._frame_count % 30 == 0  # Periodic full refresh
        )

        if needs_redraw:
            self._draw_frame()
            self._dirty_topology = False
            self._dirty_deadlock = False

        self.canvas.after(ANIMATION_FRAME_MS, self._animate)

    def _update_positions(self) -> bool:
        """Update node positions via interpolation. Returns True if any moved."""
        any_moved = False
        for pid, node in self._nodes.items():
            if self._drag_pid == pid:
                any_moved = True  # Dragging counts as movement
                continue
            if node.interpolate():
                any_moved = True
        return any_moved

    def _update_pulses(self) -> bool:
        """Advance pulse animations. Returns True if any active."""
        if not self._pulse_edges:
            return False
        done = []
        for key in self._pulse_edges:
            self._pulse_edges[key] += 0.03
            if self._pulse_edges[key] >= 1.0:
                done.append(key)
        for key in done:
            del self._pulse_edges[key]
        return True

    def _on_resize(self, event) -> None:
        self._width = event.width
        self._height = event.height
        self._dirty_topology = True

    # ─── Rendering ───

    def _draw_frame(self) -> None:
        self.canvas.delete("all")

        if not self._nodes:
            self._draw_empty_state()
            return

        self._draw_edges()
        self._draw_pulses()
        self._draw_nodes()
        self._draw_legend()

    def _draw_empty_state(self) -> None:
        """Draw the empty-state placeholder."""
        cx, cy = self._width // 2, self._height // 2
        r = GC_CANVAS["empty_ring_radius"]
        self.canvas.create_oval(
            cx - r, cy - r - 30, cx + r, cy + r - 30,
            outline="#334155", width=2, dash=(6, 4))
        self.canvas.create_text(
            cx, cy - 30,
            text="IPC", fill="#475569",
            font=("Segoe UI", 22, "bold"), justify="center")
        self.canvas.create_text(
            cx, cy + 40,
            text="No processes configured",
            fill="#94a3b8", font=("Segoe UI", 14, "bold"),
            justify="center")
        self.canvas.create_text(
            cx, cy + 65,
            text="Add processes in the Processes tab, then click Start",
            fill="#64748b", font=GUI_CONFIG["fonts"]["body"],
            justify="center")

    def _draw_edges(self) -> None:
        for conn in self._edges:
            src = self._nodes.get(conn["source"])
            dst = self._nodes.get(conn["dest"])
            if not src or not dst:
                continue

            src_snap = src.get_snapshot()
            dst_snap = dst.get_snapshot()

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
            dx = dst_snap["cx"] - src_snap["cx"]
            dy = dst_snap["cy"] - src_snap["cy"]
            dist = math.hypot(dx, dy) or 1
            r = NODE_RADIUS + 4
            ex = dst_snap["cx"] - (dx / dist) * r
            ey = dst_snap["cy"] - (dy / dist) * r
            sx = src_snap["cx"] + (dx / dist) * (NODE_RADIUS + 2)
            sy = src_snap["cy"] + (dy / dist) * (NODE_RADIUS + 2)

            self.canvas.create_line(
                sx, sy, ex, ey,
                fill=color, width=width, dash=dash if dash else None,
                arrow=tk.LAST, arrowshape=(12, 15, 5),
                smooth=True,
            )

            # Edge label at midpoint with background
            mx = (src_snap["cx"] + dst_snap["cx"]) / 2
            my = (src_snap["cy"] + dst_snap["cy"]) / 2 - 14
            label = conn.get('channel_name', '')
            ch_label = f"({ch_type})"

            self.canvas.create_text(
                mx, my, text=label, fill=COLORS["text"],
                font=GUI_CONFIG["fonts"]["edge_label"], justify="center",
            )
            self.canvas.create_text(
                mx, my + 12, text=ch_label, fill=COLORS["text_dim"],
                font=GUI_CONFIG["fonts"]["edge_sublabel"], justify="center",
            )

    def _draw_pulses(self) -> None:
        for (src_id, dst_id), phase in self._pulse_edges.items():
            src = self._nodes.get(src_id)
            dst = self._nodes.get(dst_id)
            if not src or not dst:
                continue
            src_snap = src.get_snapshot()
            dst_snap = dst.get_snapshot()
            px = src_snap["cx"] + (dst_snap["cx"] - src_snap["cx"]) * phase
            py = src_snap["cy"] + (dst_snap["cy"] - src_snap["cy"]) * phase
            # Animated glow effect
            r = 6
            alpha_r = r + 4
            self.canvas.create_oval(
                px - alpha_r, py - alpha_r, px + alpha_r, py + alpha_r,
                fill="", outline="#f1c40f", width=1, dash=(2, 2),
            )
            self.canvas.create_oval(
                px - r, py - r, px + r, py + r,
                fill="#f1c40f", outline="#f39c12", width=1,
            )

    def _draw_nodes(self) -> None:
        for pid, node in self._nodes.items():
            snap = node.get_snapshot()
            is_dl = pid in self._deadlock_nodes
            state = snap["state"]

            if is_dl:
                color = COLORS["deadlocked"]
                radius = NODE_RADIUS_DEADLOCK
                # Glow rings
                for i in range(GLOW_RINGS):
                    gr = radius + GLOW_BASE_OFFSET + i * GLOW_RING_STEP
                    alpha_colors = ["#e74c3c", "#c0392b", "#a93226"]
                    self.canvas.create_oval(
                        snap["cx"] - gr, snap["cy"] - gr,
                        snap["cx"] + gr, snap["cy"] + gr,
                        outline=alpha_colors[i], width=1, dash=(3, 3),
                    )
            else:
                color = COLORS.get(state, COLORS["idle"])
                radius = NODE_RADIUS

            # Node body with subtle shadow
            shadow_off = 3
            self.canvas.create_oval(
                snap["cx"] - radius + shadow_off,
                snap["cy"] - radius + shadow_off,
                snap["cx"] + radius + shadow_off,
                snap["cy"] + radius + shadow_off,
                fill="#0a0f1a", outline="",
            )
            self.canvas.create_oval(
                snap["cx"] - radius, snap["cy"] - radius,
                snap["cx"] + radius, snap["cy"] + radius,
                fill=color, outline="#ffffff", width=NODE_OUTLINE_WIDTH,
            )

            # Node label
            self.canvas.create_text(
                snap["cx"], snap["cy"],
                text=pid, fill="#ffffff",
                font=GUI_CONFIG["fonts"]["node_label"],
            )

            # State indicator dot below node
            indicator_y = snap["cy"] + radius + 8
            indicator_r = 3
            self.canvas.create_oval(
                snap["cx"] - indicator_r, indicator_y - indicator_r,
                snap["cx"] + indicator_r, indicator_y + indicator_r,
                fill=color, outline="",
            )

    def _draw_legend(self) -> None:
        x, y = 15, 15
        state_items = [
            ("Running", COLORS["running"]),
            ("Paused", COLORS["paused"]),
            ("Deadlocked", COLORS["deadlocked"]),
            ("Idle/Stopped", COLORS["idle"]),
        ]
        ch_items = [
            ("Pipe", COLORS["pipe"], ()),
            ("Queue", COLORS["queue"], (8, 4)),
            ("SharedMem", COLORS["shared_memory"], (2, 4)),
        ]

        total_items = len(state_items) + len(ch_items) + 1  # +1 for separator
        bw, bh = 130, total_items * 22 + 16

        # Background box
        self.canvas.create_rectangle(
            x - 5, y - 5, x + bw, y + bh,
            fill=COLORS["panel_bg"], outline=COLORS["card_bg"], width=1,
        )

        # Process states
        for label, color in state_items:
            self.canvas.create_rectangle(x, y, x + 14, y + 14, fill=color, outline="")
            self.canvas.create_text(
                x + 20, y + 7, text=label, fill=COLORS["text"],
                font=GUI_CONFIG["fonts"]["legend"], anchor="w",
            )
            y += 22

        # Separator
        y += 4
        self.canvas.create_line(x, y, x + bw - 10, y, fill=COLORS["card_bg"], width=1)
        y += 8

        # Channel types
        for label, color, dash in ch_items:
            self.canvas.create_line(x, y + 7, x + 14, y + 7,
                                     fill=color, width=2,
                                     dash=dash if dash else None)
            self.canvas.create_text(
                x + 20, y + 7, text=label, fill=COLORS["text"],
                font=GUI_CONFIG["fonts"]["legend"], anchor="w",
            )
            y += 22


# Module-level shorthand for canvas config
GC_CANVAS = GUI_CONFIG["canvas"]
