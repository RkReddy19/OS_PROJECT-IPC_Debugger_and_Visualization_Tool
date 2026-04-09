"""
Race Condition Detector — detects concurrent access to shared resources.

A race condition is flagged when:
  1. Two or more processes access the same shared resource
  2. At least one access is a write
  3. Accesses occur within a configurable time window (default: 50ms)
  4. No lock is held protecting the resource (locked=False)

FIX: locked parameter defaults to False (not True), preventing silent false negatives.
"""

import threading
import time
from typing import Dict, List, Tuple

from utils.models import RaceReport
from utils.event_logger import EventLogger


class RaceConditionDetector:
    """Detects potential race conditions by analyzing access patterns."""

    def __init__(self, logger: EventLogger, time_window: float = 0.05):
        self.logger = logger
        self.time_window = time_window  # 50ms default
        self._accesses: Dict[str, List[Tuple[float, str, str, bool]]] = {}
        self._lock = threading.Lock()

    def record_access(self, resource_name: str, pid: str,
                      access_type: str, locked: bool = False):
        """Record a resource access.

        Args:
            resource_name: Name of the shared resource
            pid: Process ID performing the access
            access_type: 'read' or 'write'
            locked: Whether a lock was held during this access
        """
        with self._lock:
            if resource_name not in self._accesses:
                self._accesses[resource_name] = []
            self._accesses[resource_name].append(
                (time.time(), pid, access_type, locked)
            )

    def detect_races(self) -> List[RaceReport]:
        """Analyze recorded accesses for potential race conditions.

        Sliding window algorithm:
        - For each resource, sort accesses by timestamp
        - For each pair of accesses within the time window:
          - If different PIDs, at least one write, and not both locked → flag
        """
        reports = []
        seen = set()  # Avoid duplicate reports for same pair

        with self._lock:
            for resource, accesses in self._accesses.items():
                accesses.sort(key=lambda x: x[0])
                for i in range(len(accesses)):
                    for j in range(i + 1, len(accesses)):
                        t1, pid1, type1, locked1 = accesses[i]
                        t2, pid2, type2, locked2 = accesses[j]

                        # Outside time window — stop inner loop
                        if t2 - t1 > self.time_window:
                            break

                        # Same process — not a race
                        if pid1 == pid2:
                            continue

                        # Both properly locked — not a race
                        if locked1 and locked2:
                            continue

                        # At least one must be a write
                        if type1 != "write" and type2 != "write":
                            continue

                        # Deduplicate
                        pair_key = (resource, frozenset([pid1, pid2]))
                        if pair_key in seen:
                            continue
                        seen.add(pair_key)

                        access_kind = ("write-write"
                                       if type1 == "write" and type2 == "write"
                                       else "read-write")
                        reports.append(RaceReport(
                            resource_name=resource,
                            accessor_pids=[pid1, pid2],
                            access_type=access_kind,
                            timestamp=t2,
                            details=(f"Concurrent {access_kind} access by "
                                     f"{pid1} and {pid2} on '{resource}' "
                                     f"within {self.time_window*1000:.0f}ms window")
                        ))

        # Log findings
        for report in reports:
            self.logger.log_event(
                source_pid="SYSTEM", dest_pid="",
                action="RACE", details=str(report)
            )
        return reports

    def reset(self):
        """Clear all recorded accesses."""
        with self._lock:
            self._accesses.clear()
