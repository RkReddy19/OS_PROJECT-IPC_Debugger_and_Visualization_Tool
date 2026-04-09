"""
IPC Debugger & Visualization Tool — Main Entry Point
Launches the Tkinter GUI application with the new package structure.
"""

import sys
import os
import logging

# Ensure the project directory is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)


def main():
    """Initialize and launch the IPC Debugger application."""
    import tkinter as tk
    from gui.app import IPCDebuggerGUI

    root = tk.Tk()
    root.title("IPC Debugger & Visualization Tool")

    # Center window on screen
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    win_w, win_h = 1400, 900
    x = (screen_w - win_w) // 2
    y = (screen_h - win_h) // 2
    root.geometry(f"{win_w}x{win_h}+{x}+{y}")

    app = IPCDebuggerGUI(root)

    # Handle graceful shutdown
    def on_close():
        try:
            app._on_stop_simulation()
            app.animated_canvas.stop_animation()
        except Exception:
            pass
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
