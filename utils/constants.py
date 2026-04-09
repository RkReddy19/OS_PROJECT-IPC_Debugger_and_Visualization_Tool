"""
Centralized Constants — Modern Dark Theme.
All colors, edge styles, thresholds, and timing configuration.
"""

# ─── Modern Color Palette ───
COLORS = {
    # Process states
    "running":     "#22c55e",
    "idle":        "#94a3b8",
    "paused":      "#f59e0b",
    "stopped":     "#64748b",
    "deadlocked":  "#ef4444",
    "waiting":     "#f59e0b",
    # Channel types
    "pipe":           "#38bdf8",
    "queue":          "#a78bfa",
    "shared_memory":  "#fb923c",
    # Edge states
    "edge_active":    "#22c55e",
    "edge_deadlock":  "#ef4444",
    "edge_idle":      "#94a3b8",
    # UI theme
    "bg":          "#0f172a",
    "bg_dark":     "#0f172a",
    "bg_darker":   "#020617",
    "text":        "#e2e8f0",
    "text_muted":  "#94a3b8",
    "text_dim":    "#64748b",
    "panel_bg":    "#1e293b",
    "card_bg":     "#334155",
    "card_hover":  "#3b4d66",
    "input_bg":    "#1e293b",
    "header_bg":   "#0f172a",
    "accent":      "#38bdf8",
    "accent_warn": "#f59e0b",
    "accent_err":  "#ef4444",
    "accent_ok":   "#22c55e",
    "info":        "#3b82f6",
    # Behavior icons
    "producer":    "#3b82f6",
    "consumer":    "#22c55e",
    "prodcons":    "#f59e0b",
    # Buttons
    "btn_primary": "#2563eb",
    "btn_primary_hover": "#3b82f6",
    "btn_success": "#16a34a",
    "btn_success_hover": "#22c55e",
    "btn_danger":  "#dc2626",
    "btn_danger_hover": "#ef4444",
    "btn_warning": "#d97706",
    "btn_warning_hover": "#f59e0b",
    "btn_secondary": "#475569",
    "btn_secondary_hover": "#64748b",
}

# ─── Behavior Emojis ───
BEHAVIOR_ICONS = {
    "producer":          "\U0001f535",  # 🔵
    "consumer":          "\U0001f7e2",  # 🟢
    "producer_consumer": "\U0001f7e1",  # 🟡
}

STATE_ICONS = {
    "running":    "\u25cf",   # ●
    "idle":       "\u25cb",   # ○
    "paused":     "\u25a0",   # ■
    "stopped":    "\u25a1",   # □
    "deadlocked": "\u2716",   # ✖
}

# ─── Edge Styles (Tkinter Canvas dash patterns) ───
EDGE_STYLES = {
    "pipe":           (),
    "queue":          (8, 4),
    "shared_memory":  (2, 4),
}

EDGE_STYLES_MPL = {
    "pipe":           "solid",
    "queue":          "dashed",
    "shared_memory":  "dotted",
}

# ─── Default Thresholds ───
DEFAULT_QUEUE_DEPTH_THRESHOLD = 10
DEFAULT_LATENCY_THRESHOLD = 2.0
DEFAULT_THROUGHPUT_RATIO_THRESHOLD = 0.5
DEFAULT_RACE_TIME_WINDOW = 0.05

# ─── Timing ───
ANIMATION_FPS = 60
ANIMATION_FRAME_MS = 1000 // ANIMATION_FPS
REFRESH_INTERVAL_MS = 2000
AUTO_DEADLOCK_INTERVAL_MS = 3000
LERP_SPEED = 0.08

# ─── Log Tag Colors & Icons ───
LOG_TAG_COLORS = {
    "SEND":         "#22c55e",
    "RECEIVE":      "#38bdf8",
    "LOCK_REQUEST": "#f59e0b",
    "LOCK_ACQUIRE": "#fb923c",
    "LOCK_RELEASE": "#94a3b8",
    "DEADLOCK":     "#ef4444",
    "BOTTLENECK":   "#fb923c",
    "RACE":         "#f87171",
    "INFO":         "#94a3b8",
    "WARNING":      "#f59e0b",
}

LOG_ICONS = {
    "SEND":         "\U0001f7e2",  # 🟢
    "RECEIVE":      "\U0001f535",  # 🔵
    "LOCK_REQUEST": "\U0001f7e1",  # 🟡
    "LOCK_ACQUIRE": "\U0001f7e0",  # 🟠
    "LOCK_RELEASE": "\u26aa",     # ⚪
    "DEADLOCK":     "\U0001f534",  # 🔴
    "BOTTLENECK":   "\u26a0\ufe0f",# ⚠️
    "RACE":         "\u26a1",     # ⚡
    "INFO":         "\u2139\ufe0f",# ℹ️
    "WARNING":      "\u26a0\ufe0f",# ⚠️
}

# ─── Node Rendering ───
NODE_RADIUS = 25
NODE_RADIUS_DEADLOCK = 30
NODE_OUTLINE_WIDTH = 2
GLOW_RINGS = 3
GLOW_BASE_OFFSET = 8
GLOW_RING_STEP = 5
