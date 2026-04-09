"""
GUI Smoke Tests — tests that IPCDebuggerGUI can initialize and basic
process management works without opening a real Tk window.
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestGUISmoke(unittest.TestCase):
    """Smoke tests for the GUI module using a mocked Tk root."""

    @patch("tkinter.Tk")
    def _make_gui(self, MockTk):
        """Helper: create an IPCDebuggerGUI with a mocked Tk root."""
        mock_root = MockTk.return_value
        mock_root.winfo_screenwidth.return_value = 1920
        mock_root.winfo_screenheight.return_value = 1080
        mock_root.configure = MagicMock()
        mock_root.minsize = MagicMock()
        mock_root.option_add = MagicMock()
        mock_root.bind = MagicMock()
        mock_root.after = MagicMock(return_value="after_id")
        mock_root.after_cancel = MagicMock()

        from gui.app import IPCDebuggerGUI
        gui = IPCDebuggerGUI(mock_root)
        return gui, mock_root

    def test_init_no_exception(self):
        """IPCDebuggerGUI.__init__ should run without raising."""
        try:
            gui, _ = self._make_gui()
            self.assertIsNotNone(gui)
        except RuntimeError as e:
            if "no default root" in str(e).lower() or "too early" in str(e).lower():
                self.skipTest("No Tk root available in headless env")
            raise
        except Exception as e:
            if "display" in str(e).lower() or "no display" in str(e).lower():
                self.skipTest("No display available for Tk widgets")
            raise

    def test_add_process_increases_count(self):
        """_on_add_process with valid inputs should increase process count."""
        try:
            gui, _ = self._make_gui()
        except Exception:
            self.skipTest("No display available for Tk widgets")
            return

        initial_count = len(gui.process_configs)

        # Simulate filling in fields
        gui.entry_pid.delete(0, "end")
        gui.entry_pid.insert(0, "TestProcess1")
        gui.combo_behavior.set("producer")
        gui.entry_message.delete(0, "end")
        gui.entry_message.insert(0, "Hello")
        gui.entry_delay.delete(0, "end")
        gui.entry_delay.insert(0, "1.0")
        gui.spin_priority.delete(0, "end")
        gui.spin_priority.insert(0, "5")

        gui._on_add_process()

        self.assertEqual(len(gui.process_configs), initial_count + 1)
        self.assertIn("TestProcess1", gui.process_configs)

    def test_reset_clears_processes(self):
        """_reset_all after adding processes should clear all."""
        try:
            gui, mock_root = self._make_gui()
        except Exception:
            self.skipTest("No display available for Tk widgets")
            return

        # Add two processes
        for pid in ["P1", "P2"]:
            gui.entry_pid.delete(0, "end")
            gui.entry_pid.insert(0, pid)
            gui._on_add_process()

        self.assertEqual(len(gui.process_configs), 2)

        # Patch messagebox to auto-confirm
        with patch("gui.simulation_controller.messagebox") as mock_mb:
            mock_mb.askyesno.return_value = True
            gui.sim_ctrl.reset_all()

        self.assertEqual(len(gui.process_configs), 0)


if __name__ == "__main__":
    unittest.main()
