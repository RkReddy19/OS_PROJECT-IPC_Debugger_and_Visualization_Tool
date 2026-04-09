"""
SharedMemoryChannel — shared variable with threading.Condition signaling.
Replaces multiprocessing.Array + multiprocessing.Event (fixes race condition).
"""

import threading
from typing import Any

from ipc.base import IPCChannel
from utils.event_logger import EventLogger


class SharedMemoryChannel(IPCChannel):
    """IPC channel simulating shared memory using threading.Condition.

    The Condition lock ensures wait/notify are atomic — no race
    between checking data_available and clearing it (Issue #3 fix).
    No 255-char limit (uses plain Python str).
    """

    def __init__(self, name: str, source_pid: str, dest_pid: str,
                 logger: EventLogger, race_detector=None):
        super().__init__(name, "shared_memory", source_pid, dest_pid, logger,
                         race_detector=race_detector)
        self._condition = threading.Condition()
        self._data = None
        self._data_available = False

    def send(self, data: Any) -> bool:
        if not self.active:
            return False
        try:
            data_str = str(data)
            data_size = len(data_str.encode('utf-8'))
            with self._condition:
                self._data = data_str
                self._data_available = True
                self._condition.notify()
            self._record_send(data_size)
            self.logger.log_event(
                source_pid=self.source_pid, dest_pid=self.dest_pid,
                action="SEND", data_size=data_size,
                details=f"SharedMem write: {data_str[:50]}",
                channel_name=self.name, channel_type="shared_memory"
            )
            return True
        except Exception as e:
            self.logger.log_event(
                source_pid=self.source_pid, dest_pid=self.dest_pid,
                action="WARNING", details=f"SharedMem write error: {e}",
                channel_name=self.name, channel_type="shared_memory"
            )
            return False

    def receive(self, timeout: float = 1.0) -> Any:
        if not self.active:
            return None
        try:
            with self._condition:
                if not self._data_available:
                    self._condition.wait(timeout=timeout)
                if self._data_available:
                    data = self._data
                    self._data_available = False
                    data_size = len(data.encode('utf-8')) if data else 0
                    self._record_receive()
                    self.logger.log_event(
                        source_pid=self.dest_pid, dest_pid=self.source_pid,
                        action="RECEIVE", data_size=data_size,
                        details=f"SharedMem read: {data[:50] if data else ''}",
                        channel_name=self.name, channel_type="shared_memory"
                    )
                    return data
        except Exception:
            pass
        return None

    def close(self):
        super().close()
        with self._condition:
            self._condition.notify_all()
