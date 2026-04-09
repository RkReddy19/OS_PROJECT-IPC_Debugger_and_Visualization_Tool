"""Tests for ipc/ — all channel types and factory."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
import threading
from utils.event_logger import EventLogger
from ipc import create_channel, PipeChannel, QueueChannel, SharedMemoryChannel


class TestPipeChannel(unittest.TestCase):
    def setUp(self):
        self.logger = EventLogger()
        self.ch = PipeChannel("test_pipe", "P1", "P2", self.logger)

    def test_send_receive(self):
        self.assertTrue(self.ch.send("hello"))
        data = self.ch.receive(timeout=1.0)
        self.assertEqual(data, "hello")

    def test_receive_timeout(self):
        data = self.ch.receive(timeout=0.1)
        self.assertIsNone(data)

    def test_close_blocks_send(self):
        self.ch.close()
        self.assertFalse(self.ch.send("data"))

    def test_stats(self):
        self.ch.send("test")
        self.ch.receive(timeout=1.0)
        stats = self.ch.get_stats()
        self.assertEqual(stats["messages_sent"], 1)
        self.assertEqual(stats["messages_received"], 1)


class TestQueueChannel(unittest.TestCase):
    def setUp(self):
        self.logger = EventLogger()
        self.ch = QueueChannel("test_q", "P1", "P2", self.logger, maxsize=10)

    def test_send_receive(self):
        self.ch.send("msg1")
        self.ch.send("msg2")
        self.assertEqual(self.ch.receive(timeout=1.0), "msg1")
        self.assertEqual(self.ch.receive(timeout=1.0), "msg2")

    def test_depth_tracking(self):
        self.ch.send("a")
        self.ch.send("b")
        self.assertEqual(self.ch.queue_depth, 2)
        self.ch.receive(timeout=1.0)
        self.assertEqual(self.ch.queue_depth, 1)

    def test_peak_depth(self):
        for i in range(5):
            self.ch.send(f"msg{i}")
        self.assertEqual(self.ch.peak_depth, 5)
        for _ in range(5):
            self.ch.receive(timeout=1.0)
        self.assertEqual(self.ch.peak_depth, 5)  # Peak stays
        self.assertEqual(self.ch.queue_depth, 0)

    def test_depth_history(self):
        self.ch.send("a")
        self.ch.receive(timeout=1.0)
        self.assertTrue(len(self.ch.depth_history) >= 2)

    def test_fifo_order(self):
        for i in range(5):
            self.ch.send(i)
        for i in range(5):
            self.assertEqual(self.ch.receive(timeout=1.0), i)


class TestSharedMemoryChannel(unittest.TestCase):
    def setUp(self):
        self.logger = EventLogger()
        self.ch = SharedMemoryChannel("test_shm", "P1", "P2", self.logger)

    def test_send_receive(self):
        self.ch.send("shared_data")
        data = self.ch.receive(timeout=1.0)
        self.assertEqual(data, "shared_data")

    def test_no_size_limit(self):
        """Unlike the old Array('c', 256), no 255-char limit."""
        big_msg = "x" * 1000
        self.ch.send(big_msg)
        data = self.ch.receive(timeout=1.0)
        self.assertEqual(data, big_msg)

    def test_receive_timeout(self):
        data = self.ch.receive(timeout=0.1)
        self.assertIsNone(data)

    def test_concurrent_send_receive(self):
        """Verify no race condition between send and receive."""
        results = []

        def sender():
            import time
            time.sleep(0.05)
            self.ch.send("concurrent_test")

        def receiver():
            data = self.ch.receive(timeout=2.0)
            results.append(data)

        t1 = threading.Thread(target=sender)
        t2 = threading.Thread(target=receiver)
        t2.start()
        t1.start()
        t1.join()
        t2.join()
        self.assertEqual(results, ["concurrent_test"])


class TestFactory(unittest.TestCase):
    def setUp(self):
        self.logger = EventLogger()

    def test_create_pipe(self):
        ch = create_channel("pipe", "c1", "A", "B", self.logger)
        self.assertIsInstance(ch, PipeChannel)

    def test_create_queue(self):
        ch = create_channel("queue", "c2", "A", "B", self.logger, maxsize=50)
        self.assertIsInstance(ch, QueueChannel)

    def test_create_shared_memory(self):
        ch = create_channel("shared_memory", "c3", "A", "B", self.logger)
        self.assertIsInstance(ch, SharedMemoryChannel)

    def test_create_with_spaces(self):
        ch = create_channel("shared memory", "c4", "A", "B", self.logger)
        self.assertIsInstance(ch, SharedMemoryChannel)

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            create_channel("unknown", "c5", "A", "B", self.logger)


if __name__ == '__main__':
    unittest.main()
