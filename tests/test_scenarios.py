"""Tests for gui/scenarios.py — preset scenario data integrity."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from gui.scenarios import load_normal_ipc, load_deadlock, load_bottleneck


class TestScenarios(unittest.TestCase):
    def test_normal_ipc(self):
        configs, connections, lock_setup = load_normal_ipc()
        self.assertIn("Producer_A", configs)
        self.assertIn("Consumer_B", configs)
        self.assertEqual(configs["Producer_A"].behavior, "producer")
        self.assertEqual(configs["Consumer_B"].behavior, "consumer")
        self.assertEqual(len(connections), 1)
        self.assertEqual(connections[0]["channel_type"], "queue")
        self.assertIsNone(lock_setup)

    def test_deadlock(self):
        configs, connections, lock_setup = load_deadlock()
        self.assertEqual(len(configs), 3)
        self.assertIn("P1", configs)
        self.assertIn("P2", configs)
        self.assertIn("P3", configs)
        self.assertEqual(len(connections), 3)
        self.assertIsNotNone(lock_setup)
        self.assertEqual(len(lock_setup), 3)
        # Check circular dependency
        lock_names = [pair[1] for pair in lock_setup]
        self.assertEqual(lock_names[0], ["Lock_A", "Lock_B"])
        self.assertEqual(lock_names[1], ["Lock_B", "Lock_C"])
        self.assertEqual(lock_names[2], ["Lock_C", "Lock_A"])

    def test_bottleneck(self):
        configs, connections, lock_setup = load_bottleneck()
        self.assertIn("FastSender", configs)
        self.assertIn("SlowReceiver", configs)
        self.assertEqual(configs["FastSender"].priority, 9)
        self.assertEqual(configs["SlowReceiver"].priority, 2)
        self.assertEqual(configs["FastSender"].delay, 0.2)
        self.assertEqual(configs["SlowReceiver"].delay, 3.0)
        self.assertEqual(len(connections), 1)
        self.assertIn("maxsize", connections[0])
        self.assertIsNone(lock_setup)


if __name__ == '__main__':
    unittest.main()
