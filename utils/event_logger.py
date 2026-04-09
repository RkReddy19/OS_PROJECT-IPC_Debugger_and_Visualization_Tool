"""
Centralized Event Logger — thread-safe logging with EventEmitter.
Emits 'new_event' on every log_event() call.
"""

import time
import threading
from collections import deque
from typing import List

from utils.models import LogEvent
from utils.event_emitter import EventEmitter


class EventLogger(EventEmitter):
    """Centralized event logging system.

    Events stored in a bounded deque and dispatched via EventEmitter.
    Emits: 'new_event' with the LogEvent as argument.
    """

    def __init__(self, maxlen: int = 10000):
        super().__init__()
        self._events: deque = deque(maxlen=maxlen)
        self._lock = threading.Lock()
        self._start_time = time.time()

    def reset(self):
        """Clear all logged events and reset start time."""
        with self._lock:
            self._events.clear()
            self._start_time = time.time()

    def log_event(self, source_pid: str, dest_pid: str, action: str,
                  data_size: int = 0, details: str = "",
                  channel_name: str = "", channel_type: str = "") -> LogEvent:
        """Log a new IPC event and emit 'new_event'."""
        event = LogEvent(
            timestamp=time.time() - self._start_time,
            source_pid=source_pid,
            dest_pid=dest_pid,
            action=action,
            data_size=data_size,
            details=details,
            channel_name=channel_name,
            channel_type=channel_type,
        )
        with self._lock:
            self._events.append(event)
        self.emit('new_event', event)
        return event

    def get_all_events(self) -> List[LogEvent]:
        """Return a copy of all logged events."""
        with self._lock:
            return list(self._events)

    def get_events_since(self, since_timestamp: float) -> List[LogEvent]:
        """Return events logged after the given relative timestamp."""
        with self._lock:
            return [e for e in self._events if e.timestamp > since_timestamp]

    def clear(self):
        """Alias for reset."""
        self.reset()

    @property
    def event_count(self) -> int:
        return len(self._events)

    @property
    def start_time(self) -> float:
        return self._start_time
