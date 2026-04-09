"""Tests for analyzers/bottleneck_detector.py — FIFO latency, thresholds."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
import time
from utils.event_logger import EventLogger
from ipc.queue_channel import QueueChannel
from ipc.pipe_channel import PipeChannel
from analyzers.bottleneck_detector import BottleneckDetector


class TestBottleneckDetector(unittest.TestCase):
    def setUp(self):
        self.logger = EventLogger()
        self.detector = BottleneckDetector(self.logger)

    def test_queue_depth_threshold(self):
        ch = QueueChannel("q1", "P1", "P2", self.logger, maxsize=50)
        for i in range(15):
            ch.send(f"msg{i}")
        self.detector.queue_depth_threshold = 10
        reports = self.detector.analyze_channels([ch])
        depth_reports = [r for r in reports if r.metric == "queue_depth"]
        self.assertGreater(len(depth_reports), 0)
        self.assertEqual(depth_reports[0].severity, "HIGH")

    def test_critical_depth(self):
        ch = QueueChannel("q1", "P1", "P2", self.logger, maxsize=50)
        for i in range(25):
            ch.send(f"msg{i}")
        self.detector.queue_depth_threshold = 10
        reports = self.detector.analyze_channels([ch])
        depth_reports = [r for r in reports if r.metric == "queue_depth"]
        self.assertEqual(depth_reports[0].severity, "CRITICAL")

    def test_no_bottleneck(self):
        ch = QueueChannel("q1", "P1", "P2", self.logger)
        ch.send("a")
        ch.receive(timeout=1.0)
        reports = self.detector.analyze_channels([ch])
        self.assertEqual(len(reports), 0)

    def test_throughput_ratio(self):
        ch = QueueChannel("q1", "P1", "P2", self.logger, maxsize=50)
        for i in range(10):
            ch.send(f"msg{i}")
        ch.receive(timeout=1.0)  # only 1 received out of 10
        reports = self.detector.analyze_channels([ch])
        ratio_reports = [r for r in reports if r.metric == "throughput_ratio"]
        self.assertGreater(len(ratio_reports), 0)

    def test_configurable_thresholds(self):
        ch = QueueChannel("q1", "P1", "P2", self.logger, maxsize=50)
        for i in range(5):
            ch.send(f"msg{i}")
        # Tight threshold → should flag
        self.detector.queue_depth_threshold = 3
        reports = self.detector.analyze_channels([ch])
        self.assertGreater(len(reports), 0)

    def test_channel_metrics(self):
        ch = QueueChannel("q1", "P1", "P2", self.logger)
        ch.send("hello")
        ch.receive(timeout=1.0)
        metrics = self.detector.get_channel_metrics([ch])
        self.assertEqual(len(metrics), 1)
        m = metrics[0]
        self.assertEqual(m.name, "q1")
        self.assertEqual(m.messages_sent, 1)
        self.assertEqual(m.messages_received, 1)

    def test_fifo_latency_pairing(self):
        """Verify FIFO-based pairing produces correct latencies."""
        ch = PipeChannel("p1", "P1", "P2", self.logger)
        # Manually inject times to test FIFO logic
        ch.send_times = [1.0, 2.0, 3.0]
        ch.receive_times = [1.5, 2.5, 3.5]
        latencies = self.detector._compute_latencies_fifo(ch)
        self.assertEqual(len(latencies), 3)
        for lat in latencies:
            self.assertAlmostEqual(lat, 0.5, places=5)


if __name__ == '__main__':
    unittest.main()
