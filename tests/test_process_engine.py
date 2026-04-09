"""Tests for engine/process_engine.py — lifecycle, behaviors."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
import time
from utils.models import ProcessConfig
from utils.event_logger import EventLogger
from ipc.queue_channel import QueueChannel
from engine.process_engine import SimulatedProcess, ProcessEngine


class TestSimulatedProcess(unittest.TestCase):
    def setUp(self):
        self.logger = EventLogger()

    def test_lifecycle(self):
        cfg = ProcessConfig(pid="P1", behavior="producer", delay=0.1)
        proc = SimulatedProcess(cfg, self.logger)
        self.assertEqual(proc.state, "idle")
        proc.start()
        self.assertEqual(proc.state, "running")
        time.sleep(0.2)
        proc.pause()
        self.assertEqual(proc.state, "paused")
        proc.resume()
        self.assertEqual(proc.state, "running")
        proc.stop()
        self.assertEqual(proc.state, "stopped")

    def test_producer_sends(self):
        cfg = ProcessConfig(pid="P1", behavior="producer", delay=0.1, message="Hi")
        ch = QueueChannel("ch1", "P1", "P2", self.logger)
        cfg.send_channels.append(ch)
        proc = SimulatedProcess(cfg, self.logger)
        proc.start()
        time.sleep(0.5)
        proc.stop()
        self.assertGreater(proc.messages_sent, 0)
        self.assertGreater(ch.queue_depth, 0)

    def test_consumer_receives(self):
        cfg = ProcessConfig(pid="P2", behavior="consumer", delay=0.1)
        ch = QueueChannel("ch1", "P1", "P2", self.logger)
        ch.send("msg1")
        ch.send("msg2")
        cfg.recv_channels.append(ch)
        proc = SimulatedProcess(cfg, self.logger)
        proc.start()
        time.sleep(0.5)
        proc.stop()
        self.assertGreater(proc.messages_received, 0)

    def test_producer_consumer_both(self):
        cfg = ProcessConfig(pid="P3", behavior="producer_consumer", delay=0.1, message="X")
        send_ch = QueueChannel("ch_out", "P3", "P4", self.logger)
        recv_ch = QueueChannel("ch_in", "P4", "P3", self.logger)
        recv_ch.send("incoming1")
        cfg.send_channels.append(send_ch)
        cfg.recv_channels.append(recv_ch)
        proc = SimulatedProcess(cfg, self.logger)
        proc.start()
        time.sleep(0.5)
        proc.stop()
        self.assertGreater(proc.messages_sent, 0)
        self.assertGreater(proc.messages_received, 0)


class TestProcessEngine(unittest.TestCase):
    def setUp(self):
        self.logger = EventLogger()
        self.engine = ProcessEngine(self.logger)

    def test_add_remove(self):
        cfg = ProcessConfig(pid="P1")
        self.engine.add_process(cfg)
        self.assertIn("P1", self.engine.processes)
        self.engine.remove_process("P1")
        self.assertNotIn("P1", self.engine.processes)

    def test_start_stop_all(self):
        for pid in ["A", "B", "C"]:
            self.engine.add_process(ProcessConfig(pid=pid, delay=0.1))
        self.engine.start_all()
        time.sleep(0.2)
        states = self.engine.get_all_states()
        for s in states.values():
            self.assertIn(s, ("running", "stopped"))
        self.engine.stop_all()

    def test_reset(self):
        self.engine.add_process(ProcessConfig(pid="P1"))
        self.engine.reset()
        self.assertEqual(len(self.engine.processes), 0)


if __name__ == '__main__':
    unittest.main()
