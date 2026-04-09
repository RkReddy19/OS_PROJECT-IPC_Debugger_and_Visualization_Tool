"""Tests for engine/sync_manager.py — TrackedLock, TrackedSemaphore."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
import threading
from utils.event_logger import EventLogger
from engine.sync_manager import TrackedLock, TrackedSemaphore, SynchronizationManager


class TestTrackedLock(unittest.TestCase):
    def setUp(self):
        self.logger = EventLogger()
        self.lock = TrackedLock("test_lock", self.logger)

    def test_acquire_release(self):
        self.assertTrue(self.lock.acquire("P1"))
        state = self.lock.get_state()
        self.assertEqual(state["holder"], "P1")
        self.lock.release("P1")
        state = self.lock.get_state()
        self.assertIsNone(state["holder"])

    def test_release_guard_wrong_holder(self):
        """Issue #2 fix: releasing a lock you don't hold should be a no-op."""
        self.lock.acquire("P1")
        self.lock.release("P2")  # Wrong holder — should be ignored
        state = self.lock.get_state()
        self.assertEqual(state["holder"], "P1")  # P1 still holds it

    def test_waiters_tracked(self):
        self.lock.acquire("P1")
        # Start P2 trying to acquire (will block)
        acquired = threading.Event()
        def try_acquire():
            self.lock.acquire("P2", timeout=0.5)
            acquired.set()

        t = threading.Thread(target=try_acquire)
        t.start()
        import time; time.sleep(0.1)
        state = self.lock.get_state()
        self.assertIn("P2", state["waiters"])
        self.lock.release("P1")
        t.join(timeout=2)

    def test_access_log(self):
        self.lock.acquire("P1")
        self.lock.release("P1")
        self.assertEqual(len(self.lock.access_log), 2)
        self.assertEqual(self.lock.access_log[0][2], "acquire")
        self.assertEqual(self.lock.access_log[1][2], "release")


class TestTrackedSemaphore(unittest.TestCase):
    def setUp(self):
        self.logger = EventLogger()
        self.sem = TrackedSemaphore("test_sem", 2, self.logger)

    def test_acquire_decrements(self):
        self.sem.acquire("P1")
        self.assertEqual(self.sem.get_state()["current_value"], 1)
        self.sem.acquire("P2")
        self.assertEqual(self.sem.get_state()["current_value"], 0)

    def test_release_increments(self):
        self.sem.acquire("P1")
        self.sem.release("P1")
        self.assertEqual(self.sem.get_state()["current_value"], 2)

    def test_holders_tracked(self):
        self.sem.acquire("P1")
        self.sem.acquire("P2")
        state = self.sem.get_state()
        self.assertIn("P1", state["holders"])
        self.assertIn("P2", state["holders"])


class TestSynchronizationManager(unittest.TestCase):
    def setUp(self):
        self.logger = EventLogger()
        self.mgr = SynchronizationManager(self.logger)

    def test_create_lock(self):
        lock = self.mgr.create_lock("L1")
        self.assertIsNotNone(lock)
        self.assertIs(self.mgr.get_lock("L1"), lock)

    def test_create_semaphore(self):
        sem = self.mgr.create_semaphore("S1", 3)
        self.assertIsNotNone(sem)
        self.assertIs(self.mgr.get_semaphore("S1"), sem)

    def test_wait_for_edges(self):
        lock = self.mgr.create_lock("L1")
        lock.acquire("P1")  # P1 holds L1

        # Simulate P2 waiting
        def waiter():
            lock.acquire("P2", timeout=0.5)
        t = threading.Thread(target=waiter)
        t.start()
        import time; time.sleep(0.1)

        edges = self.mgr.get_wait_for_edges()
        self.assertIn(("P2", "P1"), edges)
        lock.release("P1")
        t.join(timeout=2)

    def test_reset(self):
        self.mgr.create_lock("L1")
        self.mgr.create_semaphore("S1")
        self.mgr.reset()
        self.assertEqual(len(self.mgr.locks), 0)
        self.assertEqual(len(self.mgr.semaphores), 0)


if __name__ == '__main__':
    unittest.main()
