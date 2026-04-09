"""
PipeChannel — point-to-point IPC using a thread-native single-slot queue.
Replaces multiprocessing.Pipe with queue.Queue(maxsize=1).
"""

import queue
from typing import Any

from ipc.base import IPCChannel
from utils.event_logger import EventLogger


class PipeChannel(IPCChannel):
    """IPC channel simulating a pipe using a single-slot queue."""

    def __init__(self, name: str, source_pid: str, dest_pid: str,
                 logger: EventLogger, race_detector=None):
        super().__init__(name, "pipe", source_pid, dest_pid, logger,
                         race_detector=race_detector)
        self._queue = queue.Queue(maxsize=1)

    def send(self, data: Any) -> bool:
        if not self.active:
            return False
        try:
            data_str = str(data)
            data_size = len(data_str.encode('utf-8'))
            self._queue.put(data, timeout=2.0)
            self._record_send(data_size)
            self.logger.log_event(
                source_pid=self.source_pid, dest_pid=self.dest_pid,
                action="SEND", data_size=data_size,
                details=f"Data: {data_str[:50]}",
                channel_name=self.name, channel_type="pipe"
            )
            return True
        except queue.Full:
            self.logger.log_event(
                source_pid=self.source_pid, dest_pid=self.dest_pid,
                action="WARNING", details="Pipe full (blocked)",
                channel_name=self.name, channel_type="pipe"
            )
            return False
        except Exception as e:
            self.logger.log_event(
                source_pid=self.source_pid, dest_pid=self.dest_pid,
                action="WARNING", details=f"Pipe send error: {e}",
                channel_name=self.name, channel_type="pipe"
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
            self.logger.log_event(
                source_pid=self.dest_pid, dest_pid=self.source_pid,
                action="RECEIVE", data_size=data_size,
                details=f"Data: {data_str[:50]}",
                channel_name=self.name, channel_type="pipe"
            )
            return data
        except queue.Empty:
            return None
        except Exception:
            return None

    def close(self):
        super().close()
