"""
IPC Debugger — Open Landing Page
Opens the landing page in the default browser.
Usage: py launch_landing.py
"""

import os
import webbrowser

landing = os.path.join(os.path.dirname(os.path.abspath(__file__)), "landing", "index.html")

if os.path.exists(landing):
    webbrowser.open(f"file:///{landing.replace(os.sep, '/')}")
    print("Landing page opened in browser.")
    print("Click 'Explore Features' to see launch instructions.")
else:
    print(f"Landing page not found: {landing}")
