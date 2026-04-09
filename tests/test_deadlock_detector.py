"""Tests for analyzers/deadlock_detector.py — all-cycles detection."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from utils.event_logger import EventLogger
from engine.sync_manager import SynchronizationManager
from analyzers.deadlock_detector import DeadlockDetector


class TestDeadlockDetector(unittest.TestCase):
    def setUp(self):
        self.logger = EventLogger()
        self.sync = SynchronizationManager(self.logger)
        self.detector = DeadlockDetector(self.sync, self.logger)

    def test_no_cycle_empty(self):
        edges = self.detector.detect_deadlock(["P1", "P2"])
        self.assertEqual(edges, [])

    def test_no_cycle_linear(self):
        """P1 holds L1, P2 waits for L1 — no cycle."""
        import networkx as nx
        self.detector.wfg = nx.DiGraph()
        self.detector.wfg.add_edge("P2", "P1")
        # Manually call cycle detection
        self.detector.build_wait_for_graph = lambda pids: self.detector.wfg
        edges = self.detector.detect_deadlock(["P1", "P2"])
        self.assertEqual(edges, [])

    def test_two_node_cycle(self):
        """P1->P2->P1 cycle."""
        import networkx as nx
        self.detector.wfg = nx.DiGraph()
        self.detector.wfg.add_node("P1")
        self.detector.wfg.add_node("P2")
        self.detector.wfg.add_edge("P1", "P2")
        self.detector.wfg.add_edge("P2", "P1")
        # Override build to use our graph
        orig = self.detector.build_wait_for_graph
        self.detector.build_wait_for_graph = lambda pids: self.detector.wfg
        edges = self.detector.detect_deadlock(["P1", "P2"])
        self.assertGreater(len(edges), 0)
        involved = self.detector.get_involved_processes()
        self.assertIn("P1", involved)
        self.assertIn("P2", involved)

    def test_three_node_cycle(self):
        """P1->P2->P3->P1 cycle."""
        import networkx as nx
        self.detector.wfg = nx.DiGraph()
        for pid in ["P1", "P2", "P3"]:
            self.detector.wfg.add_node(pid)
        self.detector.wfg.add_edge("P1", "P2")
        self.detector.wfg.add_edge("P2", "P3")
        self.detector.wfg.add_edge("P3", "P1")
        self.detector.build_wait_for_graph = lambda pids: self.detector.wfg
        edges = self.detector.detect_deadlock(["P1", "P2", "P3"])
        self.assertGreater(len(edges), 0)
        self.assertEqual(len(self.detector.last_cycles), 1)

    def test_multiple_cycles(self):
        """Two independent cycles: P1<->P2 and P3<->P4."""
        import networkx as nx
        self.detector.wfg = nx.DiGraph()
        for pid in ["P1", "P2", "P3", "P4"]:
            self.detector.wfg.add_node(pid)
        self.detector.wfg.add_edge("P1", "P2")
        self.detector.wfg.add_edge("P2", "P1")
        self.detector.wfg.add_edge("P3", "P4")
        self.detector.wfg.add_edge("P4", "P3")
        self.detector.build_wait_for_graph = lambda pids: self.detector.wfg
        edges = self.detector.detect_deadlock(["P1", "P2", "P3", "P4"])
        self.assertGreater(len(edges), 0)
        self.assertEqual(len(self.detector.last_cycles), 2)  # Both detected

    def test_manual_dfs_matches(self):
        """Manual DFS should find cycles too."""
        import networkx as nx
        self.detector.wfg = nx.DiGraph()
        self.detector.wfg.add_edge("P1", "P2")
        self.detector.wfg.add_edge("P2", "P1")
        manual = self.detector.find_cycle_dfs_manual()
        self.assertGreater(len(manual), 0)

    def test_reset(self):
        self.detector.last_cycles = [["P1", "P2"]]
        self.detector.reset()
        self.assertEqual(self.detector.last_cycles, [])

    def test_get_graph_data(self):
        import networkx as nx
        self.detector.wfg.add_node("P1")
        data = self.detector.get_graph_data()
        self.assertIn("P1", data["nodes"])


if __name__ == '__main__':
    unittest.main()
