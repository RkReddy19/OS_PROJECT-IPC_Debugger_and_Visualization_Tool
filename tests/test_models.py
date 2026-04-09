"""Tests for utils/models.py — dataclass validation."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from utils.models import (
    LogEvent, ProcessConfig, BottleneckReport, ChannelMetrics, RaceReport
)


class TestLogEvent(unittest.TestCase):
    def test_send_str(self):
        e = LogEvent(1.234, "P1", "P2", "SEND", data_size=42,
                     channel_name="ch1", channel_type="queue")
        s = str(e)
        self.assertIn("[1.234s]", s)
        self.assertIn("P1 -> P2", s)
        self.assertIn("42B", s)

    def test_receive_str(self):
        e = LogEvent(0.5, "P2", "P1", "RECEIVE", data_size=10,
                     channel_name="ch1", channel_type="pipe")
        s = str(e)
        self.assertIn("<-", s)

    def test_deadlock_str(self):
        e = LogEvent(2.0, "SYSTEM", "", "DEADLOCK", details="Cycle: P1->P2->P1")
        self.assertIn("DEADLOCK DETECTED", str(e))

    def test_race_str(self):
        e = LogEvent(3.0, "SYSTEM", "", "RACE", details="concurrent access")
        self.assertIn("RACE CONDITION", str(e))

    def test_info_str(self):
        e = LogEvent(0.1, "P1", "", "INFO", details="started")
        s = str(e)
        self.assertIn("P1", s)
        self.assertIn("started", s)


class TestProcessConfig(unittest.TestCase):
    def test_effective_delay_high_priority(self):
        cfg = ProcessConfig(pid="P1", priority=10, delay=1.0)
        self.assertAlmostEqual(cfg.effective_delay, 0.1)

    def test_effective_delay_low_priority(self):
        cfg = ProcessConfig(pid="P1", priority=1, delay=1.0)
        self.assertAlmostEqual(cfg.effective_delay, 1.0)

    def test_effective_delay_mid_priority(self):
        cfg = ProcessConfig(pid="P1", priority=5, delay=2.0)
        expected = 2.0 * (11 - 5) / 10.0
        self.assertAlmostEqual(cfg.effective_delay, expected)

    def test_default_lists_independent(self):
        c1 = ProcessConfig(pid="A")
        c2 = ProcessConfig(pid="B")
        c1.send_channels.append("test")
        self.assertEqual(len(c2.send_channels), 0)


class TestBottleneckReport(unittest.TestCase):
    def test_str_format(self):
        r = BottleneckReport("ch1", "queue", "HIGH", "latency", 3.14, "slow")
        s = str(r)
        self.assertIn("[HIGH]", s)
        self.assertIn("3.14", s)


class TestRaceReport(unittest.TestCase):
    def test_str_format(self):
        r = RaceReport("shm1", ["P1", "P2"], "write-write", 1.0, "conflict")
        s = str(r)
        self.assertIn("[RACE]", s)
        self.assertIn("P1", s)


if __name__ == '__main__':
    unittest.main()
