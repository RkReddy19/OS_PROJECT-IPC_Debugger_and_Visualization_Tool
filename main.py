"""
IPC Debugger & Visualization Tool — Main Entry Point
Launches the Tkinter GUI application.
"""

import sys
import os
import logging
import tkinter as tk

# Ensure the project directory is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)


def show_splash(root):
    """Show a polished splash screen while Tkinter loads."""
    splash = tk.Toplevel(root)
    splash.overrideredirect(True)
    splash.configure(bg="#020617")

    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    w, h = 520, 340
    splash.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
    splash.attributes("-topmost", True)

    tk.Frame(splash, bg="#020617", height=30).pack()
    tk.Label(splash, text="⚡", font=("Segoe UI Emoji", 36),
             bg="#020617", fg="#38bdf8").pack()
    tk.Label(splash, text="IPC Debugger", font=("Segoe UI", 24, "bold"),
             bg="#020617", fg="#f1f5f9").pack(pady=(10, 2))
    tk.Label(splash, text="& Visualization Tool", font=("Segoe UI", 13),
             bg="#020617", fg="#64748b").pack()
    tk.Label(splash, text="v2.0", font=("Segoe UI", 10),
             bg="#020617", fg="#334155").pack(pady=(4, 0))

    tk.Frame(splash, bg="#020617", height=30).pack()
    bar_bg = tk.Frame(splash, bg="#1e293b", height=4, width=300)
    bar_bg.pack(pady=(10, 0))
    bar_bg.pack_propagate(False)
    bar_fill = tk.Frame(bar_bg, bg="#38bdf8", height=4, width=0)
    bar_fill.place(x=0, y=0, height=4)

    tk.Label(splash, text="Loading components...", font=("Segoe UI", 9),
             bg="#020617", fg="#475569").pack(pady=(12, 0))

    def animate_bar(step=0):
        if step <= 300:
            bar_fill.place(x=0, y=0, width=step, height=4)
            splash.after(5, animate_bar, step + 4)
        else:
            splash.destroy()

    splash.after(100, animate_bar)
    return splash


def main():
    """Initialize and launch the IPC Debugger application."""
    root = tk.Tk()
    root.withdraw()

    show_splash(root)

    def after_splash():
        root.deiconify()
        root.title("IPC Debugger & Visualization Tool")

        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()
        win_w, win_h = 1400, 900
        x = (screen_w - win_w) // 2
        y = (screen_h - win_h) // 2
        root.geometry(f"{win_w}x{win_h}+{x}+{y}")

        from gui.app import IPCDebuggerGUI
        app = IPCDebuggerGUI(root)

        def on_close():
            try:
                app.sim_ctrl.stop_simulation()
                app.animated_canvas.stop_animation()
            except Exception:
                pass
            root.destroy()

        root.protocol("WM_DELETE_WINDOW", on_close)

    root.after(1600, after_splash)
    root.mainloop()


if __name__ == "__main__":
    main()
