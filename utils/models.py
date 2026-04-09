"""
Core Data Models for the IPC Debugger.
All @dataclass definitions centralized in one location.
"""

from dataclasses import dataclass, field
from typing import List, Any


@dataclass
class LogEvent:
    """Represents a single IPC/system event."""
    timestamp: float
    source_pid: str
    dest_pid: str
    action: str  # SEND, RECEIVE, LOCK_REQUEST, LOCK_ACQUIRE, LOCK_RELEASE, DEADLOCK, BOTTLENECK, RACE, INFO, WARNING
    data_size: int = 0
    details: str = ""
    channel_name: str = ""
    channel_type: str = ""

    def __str__(self):
        ts = f"{self.timestamp:.3f}s"
        parts = [f"[{ts}]"]
        if self.action in ("SEND", "RECEIVE"):
            direction = "->" if self.action == "SEND" else "<-"
            parts.append(f"{self.source_pid} {direction} {self.dest_pid}")
            parts.append(f"({self.channel_type}:{self.channel_name})")
            if self.data_size > 0:
                parts.append(f"{self.data_size}B")
        elif self.action in ("LOCK_REQUEST", "LOCK_ACQUIRE", "LOCK_RELEASE"):
            parts.append(f"{self.source_pid} {self.action}")
            if self.details:
                parts.append(f"[{self.details}]")
        elif self.action == "DEADLOCK":
            parts.append(f"DEADLOCK DETECTED: {self.details}")
        elif self.action == "BOTTLENECK":
            parts.append(f"BOTTLENECK: {self.details}")
        elif self.action == "RACE":
            parts.append(f"RACE CONDITION: {self.details}")
        else:
            parts.append(f"{self.source_pid}: {self.action}")
            if self.details:
                parts.append(f"- {self.details}")
        return " ".join(parts)


@dataclass
class ProcessConfig:
    """Configuration for a simulated process."""
    pid: str
    priority: int = 5
    behavior: str = "producer"
    message: str = "Hello"
    delay: float = 1.0
    send_channels: List[Any] = field(default_factory=list)
    recv_channels: List[Any] = field(default_factory=list)
    locks_to_acquire: List[Any] = field(default_factory=list)

    @property
    def effective_delay(self) -> float:
        """Higher priority -> shorter delay."""
        return self.delay * (11 - self.priority) / 10.0


@dataclass
class BottleneckReport:
    """Report for a single detected bottleneck."""
    channel_name: str
    channel_type: str
    severity: str   # LOW, MEDIUM, HIGH, CRITICAL
    metric: str     # queue_depth, latency, throughput_ratio
    value: float
    details: str

    def __str__(self):
        return (f"[{self.severity}] {self.channel_name} ({self.channel_type}): "
                f"{self.metric}={self.value:.2f} — {self.details}")


@dataclass
class ChannelMetrics:
    """Performance metrics for a single IPC channel."""
    name: str
    channel_type: str
    source: str
    dest: str
    messages_sent: int = 0
    messages_received: int = 0
    total_bytes: int = 0
    avg_latency: float = 0.0
    max_latency: float = 0.0
    queue_depth: int = 0
    max_queue_size: int = 0
    peak_depth: int = 0
    throughput: float = 0.0


@dataclass
class RaceReport:
    """Report for a detected potential race condition."""
    resource_name: str
    accessor_pids: List[str] = field(default_factory=list)
    access_type: str = ""   # read-write, write-write
    timestamp: float = 0.0
    details: str = ""

    def __str__(self):
        return (f"[RACE] {self.resource_name}: {self.access_type} by "
                f"{', '.join(self.accessor_pids)} — {self.details}")
