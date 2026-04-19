"""
Process Simulation Engine — spawns simulated processes using threads.
Each process runs a behavior loop (producer, consumer, producer_consumer)
and can be paused/resumed/stopped.

Enhancements:
- Custom exception classes for granular error handling
- Retry logic for transient lock failures
- Full type hints throughout
- Thread-safe message counters
FIX: producer_consumer now properly sends AND receives.
"""

import threading
import time
from typing import Dict, List, Optional

from utils.models import ProcessConfig
from utils.event_logger import EventLogger
from utils.exceptions import (
    LockTimeoutException,
    ChannelException,
    ProcessException,
)
from utils.constants import PROCESS_ENGINE_CONFIG as PE_CFG
from ipc.base import IPCChannel
from engine.sync_manager import TrackedLock


class SimulatedProcess:
    """Wraps a thread that executes a process behavior loop.

    Provides robust error handling with distinct handling for:
    - Lock timeouts (may indicate deadlock — retried then escalated)
    - Channel errors (transient — retried with backoff)
    - Unexpected exceptions (logged and process moves to error state)
    """

    def __init__(self, config: ProcessConfig, logger: EventLogger) -> None:
        self.config: ProcessConfig = config
        self.logger: EventLogger = logger
        self._thread: Optional[threading.Thread] = None
        self._stop_event: threading.Event = threading.Event()
        self._pause_event: threading.Event = threading.Event()
        self._pause_event.set()  # not paused by default
        self.state: str = "idle"
        self.messages_sent: int = 0
        self.messages_received: int = 0
        self._counter_lock: threading.Lock = threading.Lock()

    # ── Lifecycle ──

    def start(self) -> None:
        """Start the simulated process."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._pause_event.set()
        self.state = "running"
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self.logger.log_event(
            source_pid=self.config.pid, dest_pid="",
            action="INFO",
            details=f"Process started (behavior={self.config.behavior})"
        )

    def pause(self) -> None:
        """Pause the process (blocks the behavior loop)."""
        self._pause_event.clear()
        self.state = "paused"
        self.logger.log_event(
            source_pid=self.config.pid, dest_pid="",
            action="INFO", details="Process paused"
        )

    def resume(self) -> None:
        """Resume the process from paused state."""
        self._pause_event.set()
        self.state = "running"
        self.logger.log_event(
            source_pid=self.config.pid, dest_pid="",
            action="INFO", details="Process resumed"
        )

    def stop(self) -> None:
        """Stop the process and join the thread."""
        self._stop_event.set()
        self._pause_event.set()  # unblock if paused
        self.state = "stopped"
        if self._thread:
            self._thread.join(timeout=3)
        self.logger.log_event(
            source_pid=self.config.pid, dest_pid="",
            action="INFO", details="Process stopped"
        )

    def mark_deadlocked(self) -> None:
        """Mark the process as deadlocked."""
        self.state = "deadlocked"

    # ── Main Loop ──

    def _run(self) -> None:
        """Main execution loop for the simulated process."""
        behavior: str = self.config.behavior.lower()
        try:
            # Phase 1: Acquire locks (for deadlock scenarios)
            self._acquire_locks_with_retry()

            # Phase 2: Main behavior loop
            iteration: int = 0
            while not self._stop_event.is_set():
                self._pause_event.wait()
                if self._stop_event.is_set():
                    break

                try:
                    if behavior == "producer":
                        self._do_send_safe(iteration)
                    elif behavior == "consumer":
                        self._do_receive_safe()
                    elif behavior == "producer_consumer":
                        # FIX: properly interleave send and receive
                        self._do_send_safe(iteration)
                        self._do_receive_safe()

                    iteration += 1

                except ChannelException as e:
                    # Channel temporarily unavailable — expected, retry
                    self.logger.log_event(
                        source_pid=self.config.pid, dest_pid="",
                        action="DEBUG",
                        details=f"Channel unavailable (will retry): {e}",
                    )
                    time.sleep(PE_CFG["retry_delay_channel"])

                except LockTimeoutException as e:
                    # Lock timeout — process is blocked, possible deadlock
                    self.logger.log_event(
                        source_pid=self.config.pid, dest_pid="",
                        action="WARNING",
                        details=f"Lock timeout (possible deadlock): {e}",
                    )
                    self.state = "waiting"
                    time.sleep(PE_CFG["retry_delay_lock"])

                except ProcessException as e:
                    # Known process error — log and continue
                    self.logger.log_event(
                        source_pid=self.config.pid, dest_pid="",
                        action="WARNING",
                        details=f"Process error: {e}",
                    )

                except Exception as e:
                    # Unexpected error — log and stop this process
                    self.logger.log_event(
                        source_pid=self.config.pid, dest_pid="",
                        action="ERROR",
                        details=f"Unexpected error in {behavior}: "
                                f"{type(e).__name__}: {e}",
                    )
                    self.state = "error"
                    break

                time.sleep(self.config.effective_delay)

        except LockTimeoutException as e:
            # Fatal lock timeout during initialization
            self.logger.log_event(
                source_pid=self.config.pid, dest_pid="",
                action="WARNING",
                details=f"Lock acquisition failed after retries: {e}",
            )
            self.state = "waiting"

        except Exception as e:
            # Fatal error during initialization
            self.logger.log_event(
                source_pid=self.config.pid, dest_pid="",
                action="ERROR",
                details=f"Fatal initialization error: {type(e).__name__}: {e}",
            )
            self.state = "error"

        finally:
            # Always clean up locks
            self._release_locks_safely()
            if self.state not in ("stopped", "error", "waiting"):
                self.state = "stopped"

    # ── Lock Handling ──

    def _acquire_locks_with_retry(self) -> None:
        """Acquire all configured locks with retry logic."""
        max_retries: int = PE_CFG["max_lock_retries"]
        timeout: float = PE_CFG["lock_acquire_timeout"]

        for lock in self.config.locks_to_acquire:
            if self._stop_event.is_set():
                return
            self._pause_event.wait()

            acquired = False
            for retry in range(max_retries):
                if self._stop_event.is_set():
                    return

                success = lock.acquire(
                    self.config.pid,
                    blocking=True,
                    timeout=timeout,
                )
                if success:
                    acquired = True
                    time.sleep(PE_CFG["lock_hold_delay"])
                    break
                else:
                    if retry < max_retries - 1:
                        self.logger.log_event(
                            source_pid=self.config.pid, dest_pid="",
                            action="DEBUG",
                            details=f"Lock retry {retry + 1}/{max_retries} "
                                    f"for {lock.name}",
                        )
                        time.sleep(PE_CFG["retry_delay_lock"])

            if not acquired:
                raise LockTimeoutException(
                    f"Lock '{lock.name}' acquisition failed "
                    f"after {max_retries} retries"
                )

    def _release_locks_safely(self) -> None:
        """Release all held locks, catching and logging errors."""
        for lock in self.config.locks_to_acquire:
            try:
                lock.release(self.config.pid)
            except Exception as e:
                self.logger.log_event(
                    source_pid=self.config.pid, dest_pid="",
                    action="WARNING",
                    details=f"Error releasing lock '{lock.name}': {e}",
                )

    # ── Channel Operations ──

    def _do_send_safe(self, iteration: int) -> None:
        """Send a message to all send channels with error handling."""
        msg: str = f"{self.config.message}_{iteration}"
        for ch in self.config.send_channels:
            try:
                if ch.send(msg):
                    with self._counter_lock:
                        self.messages_sent += 1
            except Exception as e:
                raise ChannelException(
                    f"Send failed on '{ch.name}': {e}"
                ) from e

    def _do_receive_safe(self) -> None:
        """Receive a message from all receive channels with error handling."""
        for ch in self.config.recv_channels:
            try:
                data = ch.receive(timeout=PE_CFG["receive_timeout"])
                if data is not None:
                    with self._counter_lock:
                        self.messages_received += 1
            except Exception as e:
                raise ChannelException(
                    f"Receive failed on '{ch.name}': {e}"
                ) from e


class ProcessEngine:
    """Manages all simulated processes."""

    def __init__(self, logger: EventLogger) -> None:
        self.logger: EventLogger = logger
        self.processes: Dict[str, SimulatedProcess] = {}

    def add_process(self, config: ProcessConfig) -> SimulatedProcess:
        """Create and register a new simulated process."""
        proc = SimulatedProcess(config, self.logger)
        self.processes[config.pid] = proc
        return proc

    def remove_process(self, pid: str) -> None:
        """Stop and remove a process by PID."""
        if pid in self.processes:
            self.processes[pid].stop()
            del self.processes[pid]

    def start_all(self) -> None:
        """Start all idle/stopped processes."""
        for proc in self.processes.values():
            if proc.state in ("idle", "stopped"):
                proc.start()

    def pause_all(self) -> None:
        """Pause all running processes."""
        for proc in self.processes.values():
            if proc.state == "running":
                proc.pause()

    def resume_all(self) -> None:
        """Resume all paused processes."""
        for proc in self.processes.values():
            if proc.state == "paused":
                proc.resume()

    def stop_all(self) -> None:
        """Stop all processes."""
        for proc in self.processes.values():
            proc.stop()

    def get_process(self, pid: str) -> Optional[SimulatedProcess]:
        """Get a process by PID, or None if not found."""
        return self.processes.get(pid)

    def get_all_states(self) -> Dict[str, str]:
        """Return a dict mapping PID → state string."""
        return {pid: p.state for pid, p in self.processes.items()}

    def reset(self) -> None:
        """Stop all processes and clear the registry."""
        self.stop_all()
        self.processes.clear()
