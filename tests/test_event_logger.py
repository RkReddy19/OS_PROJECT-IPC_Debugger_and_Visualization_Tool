"""Tests for utils/event_logger.py — thread safety, callbacks, bounds."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
import threading
from utils.event_logger import EventLogger


class TestEventLogger(unittest.TestCase):
    def setUp(self):
        self.logger = EventLogger()

    def test_log_event_basic(self):
        e = self.logger.log_event("P1", "P2", "SEND", data_size=10)
        self.assertEqual(e.source_pid, "P1")
        self.assertEqual(e.action, "SEND")
        self.assertEqual(self.logger.event_count, 1)

    def test_get_all_events(self):
        self.logger.log_event("P1", "", "INFO")
        self.logger.log_event("P2", "", "INFO")
        events = self.logger.get_all_events()
        self.assertEqual(len(events), 2)

    def test_reset_clears(self):
        self.logger.log_event("P1", "", "INFO")
        self.logger.reset()
        self.assertEqual(self.logger.event_count, 0)

    def test_bounded_deque(self):
        logger = EventLogger(maxlen=5)
        for i in range(10):
            logger.log_event("P1", "", "INFO", details=str(i))
        self.assertEqual(logger.event_count, 5)
        events = logger.get_all_events()
        self.assertEqual(events[0].details, "5")

    def test_callback_fires(self):
        received = []
        self.logger.on('new_event', lambda e: received.append(e))
        self.logger.log_event("P1", "", "INFO")
        self.assertEqual(len(received), 1)

    def test_callback_error_does_not_crash(self):
        def bad_callback(e):
            raise ValueError("boom")
        self.logger.on('new_event', bad_callback)
        # Should not raise
        self.logger.log_event("P1", "", "INFO")

    def test_thread_safety(self):
        """10 threads, 100 events each = 1000 total."""
        barrier = threading.Barrier(10)

        def writer(tid):
            barrier.wait()
            for i in range(100):
                self.logger.log_event(f"T{tid}", "", "INFO", details=str(i))

        threads = [threading.Thread(target=writer, args=(t,)) for t in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(self.logger.event_count, 1000)

    def test_get_events_since(self):
        e1 = self.logger.log_event("P1", "", "INFO")
        e2 = self.logger.log_event("P2", "", "INFO")
        events = self.logger.get_events_since(e1.timestamp)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].source_pid, "P2")


if __name__ == '__main__':
    unittest.main()
