"""Tests for analyzers/race_detector.py — concurrent access detection."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
import time
from utils.event_logger import EventLogger
from analyzers.race_detector import RaceConditionDetector


class TestRaceConditionDetector(unittest.TestCase):
    def setUp(self):
        self.logger = EventLogger()
        self.detector = RaceConditionDetector(self.logger, time_window=0.1)

    def test_write_write_detected(self):
        now = time.time()
        self.detector.record_access("shm1", "P1", "write")
        self.detector.record_access("shm1", "P2", "write")
        reports = self.detector.detect_races()
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0].access_type, "write-write")

    def test_read_write_detected(self):
        self.detector.record_access("shm1", "P1", "read")
        self.detector.record_access("shm1", "P2", "write")
        reports = self.detector.detect_races()
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0].access_type, "read-write")

    def test_read_read_not_flagged(self):
        self.detector.record_access("shm1", "P1", "read")
        self.detector.record_access("shm1", "P2", "read")
        reports = self.detector.detect_races()
        self.assertEqual(len(reports), 0)

    def test_locked_access_not_flagged(self):
        """Both locked → no race."""
        self.detector.record_access("shm1", "P1", "write", locked=True)
        self.detector.record_access("shm1", "P2", "write", locked=True)
        reports = self.detector.detect_races()
        self.assertEqual(len(reports), 0)

    def test_same_pid_not_flagged(self):
        self.detector.record_access("shm1", "P1", "write")
        self.detector.record_access("shm1", "P1", "write")
        reports = self.detector.detect_races()
        self.assertEqual(len(reports), 0)

    def test_outside_window_not_flagged(self):
        self.detector.time_window = 0.01  # 10ms
        self.detector.record_access("shm1", "P1", "write")
        time.sleep(0.05)  # 50ms > 10ms window
        self.detector.record_access("shm1", "P2", "write")
        reports = self.detector.detect_races()
        self.assertEqual(len(reports), 0)

    def test_reset(self):
        self.detector.record_access("shm1", "P1", "write")
        self.detector.reset()
        reports = self.detector.detect_races()
        self.assertEqual(len(reports), 0)

    def test_multiple_resources(self):
        self.detector.record_access("shm1", "P1", "write")
        self.detector.record_access("shm1", "P2", "write")
        self.detector.record_access("shm2", "P3", "write")
        self.detector.record_access("shm2", "P4", "write")
        reports = self.detector.detect_races()
        self.assertEqual(len(reports), 2)

    def test_deduplication(self):
        """Same pair on same resource should only be reported once."""
        self.detector.record_access("shm1", "P1", "write")
        self.detector.record_access("shm1", "P2", "write")
        self.detector.record_access("shm1", "P1", "write")
        self.detector.record_access("shm1", "P2", "write")
        reports = self.detector.detect_races()
        # Should be deduplicated to 1 report for (shm1, {P1,P2})
        self.assertEqual(len(reports), 1)


if __name__ == '__main__':
    unittest.main()
