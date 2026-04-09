"""
QueueChannel — FIFO IPC with depth and peak tracking.
Replaces multiprocessing.Queue with thread-native queue.Queue.
"""

import queue
import threading
import time
from typing import Any, List, Tuple

from ipc.base import IPCChannel
from utils.event_logger import EventLogger


class QueueChannel(IPCChannel):
    """IPC channel backed by a thread-native queue with depth tracking."""

    def __init__(self, name: str, source_pid: str, dest_pid: str,
                 logger: EventLogger, maxsize: int = 100,
                 race_detector=None):
        super().__init__(name, "queue", source_pid, dest_pid, logger,
                         race_detector=race_detector)
        self._queue = queue.Queue(maxsize=maxsize)
        self.maxsize = maxsize
        self._depth = 0
        self._peak_depth = 0
        self._depth_lock = threading.Lock()
        self.depth_history: List[Tuple[float, int]] = []

    @property
    def queue_depth(self) -> int:
        with self._depth_lock:
            return self._depth

    @property
    def peak_depth(self) -> int:
        with self._depth_lock:
            return self._peak_depth

    def send(self, data: Any) -> bool:
        if not self.active:
            return False
        try:
            data_str = str(data)
            data_size = len(data_str.encode('utf-8'))
            self._queue.put(data, timeout=2.0)
            self._record_send(data_size)
            with self._depth_lock:
                self._depth += 1
                if self._depth > self._peak_depth:
                    self._peak_depth = self._depth
                self.depth_history.append((time.time(), self._depth))
            self.logger.log_event(
                source_pid=self.source_pid, dest_pid=self.dest_pid,
                action="SEND", data_size=data_size,
                details=f"Data: {data_str[:50]} | Depth: {self._depth}",
                channel_name=self.name, channel_type="queue"
            )
            return True
        except queue.Full:
            self.logger.log_event(
                source_pid=self.source_pid, dest_pid=self.dest_pid,
                action="WARNING", details="Queue full",
                channel_name=self.name, channel_type="queue"
            )
            return False
        except Exception as e:
            self.logger.log_event(
                source_pid=self.source_pid, dest_pid=self.dest_pid,
                action="WARNING", details=f"Queue send error: {e}",
                channel_name=self.name, channel_type="queue"
            )
            return False

    def receive(self, timeout: float = 1.0) -> Any:
        if not self.active:
            return None
        try:
            data = self._queue.get(timeout=timeout)
            data_str = str(data)
            data_size = len(data_str.encode('utf-8'))
            self._record_receive()
            with self._depth_lock:
                self._depth = max(0, self._depth - 1)
                self.depth_history.append((time.time(), self._depth))
            self.logger.log_event(
                source_pid=self.dest_pid, dest_pid=self.source_pid,
                action="RECEIVE", data_size=data_size,
                details=f"Data: {data_str[:50]} | Depth: {self._depth}",
                channel_name=self.name, channel_type="queue"
            )
            return data
        except queue.Empty:
            return None
        except Exception:
            return None

    def close(self):
        super().close()
