"""
IPCChannel Abstract Base Class.
All channel implementations inherit from this.
"""

import time
import threading
from abc import ABC, abstractmethod
from collections import deque
from typing import Any, List, Optional

from utils.event_logger import EventLogger


class IPCChannel(ABC):
    """Base class for all IPC channel types."""

    # Maximum number of timing records to retain per channel
    _MAX_TIMING_RECORDS = 5000

    def __init__(self, name: str, channel_type: str, source_pid: str,
                 dest_pid: str, logger: EventLogger,
                 race_detector=None):
        self.name = name
        self.channel_type = channel_type
        self.source_pid = source_pid
        self.dest_pid = dest_pid
        self.logger = logger
        self.race_detector = race_detector
        self.message_count = 0
        self.total_bytes = 0
        self.send_times: deque = deque(maxlen=self._MAX_TIMING_RECORDS)
        self.receive_times: deque = deque(maxlen=self._MAX_TIMING_RECORDS)
        self.active = True
        self._stats_lock = threading.Lock()

    @abstractmethod
    def send(self, data: Any) -> bool:
        """Send data through the channel. Returns True on success."""
        ...

    @abstractmethod
    def receive(self, timeout: float = 1.0) -> Any:
        """Receive data from the channel. Returns None on timeout/error."""
        ...

    def close(self):
        """Mark the channel as inactive."""
        self.active = False

    def get_stats(self) -> dict:
        """Return channel statistics."""
        with self._stats_lock:
            return {
                "name": self.name,
                "type": self.channel_type,
                "source": self.source_pid,
                "dest": self.dest_pid,
                "message_count": self.message_count,
                "total_bytes": self.total_bytes,
                "messages_sent": len(self.send_times),
                "messages_received": len(self.receive_times),
            }

    def _record_send(self, data_size: int):
        """Record a successful send (thread-safe)."""
        with self._stats_lock:
            self.message_count += 1
            self.total_bytes += data_size
            self.send_times.append(time.time())
        # Auto-record for race detection
        if self.race_detector is not None:
            self.race_detector.record_access(
                self.name, self.source_pid, "write", locked=False)

    def _record_receive(self):
        """Record a successful receive (thread-safe)."""
        with self._stats_lock:
            self.receive_times.append(time.time())
        # Auto-record for race detection
        if self.race_detector is not None:
            self.race_detector.record_access(
                self.name, self.dest_pid, "read", locked=False)
