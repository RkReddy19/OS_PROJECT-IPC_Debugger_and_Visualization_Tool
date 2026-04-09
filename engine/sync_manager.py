"""
Synchronization Manager — TrackedLock, TrackedSemaphore, and central registry.
FIX: TrackedLock.release() only releases if caller is the actual holder (Issue #2).
Tracks access timestamps for the RaceConditionDetector.
"""

import threading
import time
from typing import Dict, List, Optional, Set, Tuple

from utils.event_logger import EventLogger


class TrackedLock:
    """A lock wrapper that records who holds it and who is waiting."""

    def __init__(self, name: str, logger: EventLogger):
        self.name = name
        self.logger = logger
        self._lock = threading.Lock()
        self._meta_lock = threading.Lock()
        self.holder: Optional[str] = None
        self.waiters: Set[str] = set()
        self.access_log: List[Tuple[float, str, str]] = []

    def acquire(self, process_id: str, blocking: bool = True,
                timeout: float = -1) -> bool:
        """Attempt to acquire the lock for the given process."""
        with self._meta_lock:
            self.waiters.add(process_id)
        self.logger.log_event(
            source_pid=process_id, dest_pid="",
            action="LOCK_REQUEST", details=self.name
        )
        if timeout > 0:
            acquired = self._lock.acquire(blocking=blocking, timeout=timeout)
        else:
            acquired = self._lock.acquire(blocking=blocking)

        with self._meta_lock:
            self.waiters.discard(process_id)
            if acquired:
                self.holder = process_id
                self.access_log.append((time.time(), process_id, "acquire"))
        if acquired:
            self.logger.log_event(
                source_pid=process_id, dest_pid="",
                action="LOCK_ACQUIRE", details=self.name
            )
        return acquired

    def release(self, process_id: str):
        """Release the lock — ONLY if caller is the actual holder (Issue #2 fix)."""
        with self._meta_lock:
            if self.holder != process_id:
                return  # Don't release if not the holder
            self.holder = None
            self.access_log.append((time.time(), process_id, "release"))
        try:
            self._lock.release()
        except RuntimeError:
            pass
        self.logger.log_event(
            source_pid=process_id, dest_pid="",
            action="LOCK_RELEASE", details=self.name
        )

    def get_state(self) -> dict:
        with self._meta_lock:
            return {
                "name": self.name,
                "holder": self.holder,
                "waiters": list(self.waiters),
            }


class TrackedSemaphore:
    """A semaphore wrapper with counter tracking."""

    def __init__(self, name: str, value: int, logger: EventLogger):
        self.name = name
        self.logger = logger
        self._semaphore = threading.Semaphore(value)
        self._meta_lock = threading.Lock()
        self.max_value = value
        self.current_value = value
        self.holders: Set[str] = set()
        self.waiters: Set[str] = set()
        self.access_log: List[Tuple[float, str, str]] = []

    def acquire(self, process_id: str, blocking: bool = True,
                timeout: float = -1) -> bool:
        with self._meta_lock:
            self.waiters.add(process_id)
        self.logger.log_event(
            source_pid=process_id, dest_pid="",
            action="LOCK_REQUEST", details=f"Semaphore:{self.name}"
        )
        if timeout > 0:
            acquired = self._semaphore.acquire(blocking=blocking, timeout=timeout)
        else:
            acquired = self._semaphore.acquire(blocking=blocking)

        with self._meta_lock:
            self.waiters.discard(process_id)
            if acquired:
                self.holders.add(process_id)
                self.current_value -= 1
                self.access_log.append((time.time(), process_id, "acquire"))
        if acquired:
            self.logger.log_event(
                source_pid=process_id, dest_pid="",
                action="LOCK_ACQUIRE", details=f"Semaphore:{self.name}"
            )
        return acquired

    def release(self, process_id: str):
        with self._meta_lock:
            self.holders.discard(process_id)
            self.current_value += 1
            self.access_log.append((time.time(), process_id, "release"))
        self._semaphore.release()
        self.logger.log_event(
            source_pid=process_id, dest_pid="",
            action="LOCK_RELEASE", details=f"Semaphore:{self.name}"
        )

    def get_state(self) -> dict:
        with self._meta_lock:
            return {
                "name": self.name,
                "holders": list(self.holders),
                "waiters": list(self.waiters),
                "current_value": self.current_value,
                "max_value": self.max_value,
            }


class SynchronizationManager:
    """Central registry of all tracked synchronization primitives."""

    def __init__(self, logger: EventLogger):
        self.logger = logger
        self.locks: Dict[str, TrackedLock] = {}
        self.semaphores: Dict[str, TrackedSemaphore] = {}
        self._reg_lock = threading.Lock()

    def create_lock(self, name: str) -> TrackedLock:
        with self._reg_lock:
            lock = TrackedLock(name, self.logger)
            self.locks[name] = lock
            return lock

    def create_semaphore(self, name: str, value: int = 1) -> TrackedSemaphore:
        with self._reg_lock:
            sem = TrackedSemaphore(name, value, self.logger)
            self.semaphores[name] = sem
            return sem

    def get_lock(self, name: str) -> Optional[TrackedLock]:
        return self.locks.get(name)

    def get_semaphore(self, name: str) -> Optional[TrackedSemaphore]:
        return self.semaphores.get(name)

    def get_all_lock_states(self) -> List[dict]:
        """Return lock states for deadlock detection."""
        states = []
        for lock in self.locks.values():
            states.append(lock.get_state())
        for sem in self.semaphores.values():
            states.append(sem.get_state())
        return states

    def get_wait_for_edges(self) -> List[tuple]:
        """Build wait-for edges: (waiter_pid, holder_pid).
        Used by the deadlock detector to build the WFG."""
        edges = []
        for lock in self.locks.values():
            state = lock.get_state()
            if state["holder"]:
                for waiter in state["waiters"]:
                    edges.append((waiter, state["holder"]))
        for sem in self.semaphores.values():
            state = sem.get_state()
            if state["current_value"] <= 0:
                for waiter in state["waiters"]:
                    for holder in state["holders"]:
                        if waiter != holder:
                            edges.append((waiter, holder))
        return edges

    def get_all_access_logs(self) -> Dict[str, List[Tuple[float, str, str]]]:
        """Return access logs for all primitives (used by race detector)."""
        logs = {}
        for name, lock in self.locks.items():
            logs[name] = list(lock.access_log)
        for name, sem in self.semaphores.items():
            logs[f"sem:{name}"] = list(sem.access_log)
        return logs

    def reset(self):
        """Clear all tracked primitives."""
        with self._reg_lock:
            self.locks.clear()
            self.semaphores.clear()
