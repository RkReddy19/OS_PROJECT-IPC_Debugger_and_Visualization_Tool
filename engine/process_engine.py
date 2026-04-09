"""
Process Simulation Engine — spawns simulated processes using threads.
Each process runs a behavior loop (producer, consumer, producer_consumer)
and can be paused/resumed/stopped.
FIX: producer_consumer now properly sends AND receives.
"""

import threading
import time
from typing import Dict, List, Optional

from utils.models import ProcessConfig
from utils.event_logger import EventLogger
from ipc.base import IPCChannel
from engine.sync_manager import TrackedLock


class SimulatedProcess:
    """Wraps a thread that executes a process behavior loop."""

    def __init__(self, config: ProcessConfig, logger: EventLogger):
        self.config = config
        self.logger = logger
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # not paused by default
        self.state = "idle"
        self.messages_sent = 0
        self.messages_received = 0

    def start(self):
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

    def pause(self):
        self._pause_event.clear()
        self.state = "paused"
        self.logger.log_event(
            source_pid=self.config.pid, dest_pid="",
            action="INFO", details="Process paused"
        )

    def resume(self):
        self._pause_event.set()
        self.state = "running"
        self.logger.log_event(
            source_pid=self.config.pid, dest_pid="",
            action="INFO", details="Process resumed"
        )

    def stop(self):
        self._stop_event.set()
        self._pause_event.set()  # unblock if paused
        self.state = "stopped"
        if self._thread:
            self._thread.join(timeout=3)
        self.logger.log_event(
            source_pid=self.config.pid, dest_pid="",
            action="INFO", details="Process stopped"
        )

    def mark_deadlocked(self):
        self.state = "deadlocked"

    def _run(self):
        """Main execution loop for the simulated process."""
        behavior = self.config.behavior.lower()
        try:
            # Acquire locks first (for deadlock scenarios)
            for lock in self.config.locks_to_acquire:
                if self._stop_event.is_set():
                    return
                self._pause_event.wait()
                lock.acquire(self.config.pid, blocking=True, timeout=5)
                time.sleep(0.2)  # Hold briefly so deadlocks can form

            iteration = 0
            while not self._stop_event.is_set():
                self._pause_event.wait()
                if self._stop_event.is_set():
                    break

                if behavior == "producer":
                    self._do_send(iteration)
                elif behavior == "consumer":
                    self._do_receive()
                elif behavior == "producer_consumer":
                    # FIX: properly interleave send and receive
                    self._do_send(iteration)
                    self._do_receive()

                iteration += 1
                time.sleep(self.config.effective_delay)

        except Exception as e:
            self.logger.log_event(
                source_pid=self.config.pid, dest_pid="",
                action="WARNING", details=f"Process error: {e}"
            )
        finally:
            # Release any held locks
            for lock in self.config.locks_to_acquire:
                try:
                    lock.release(self.config.pid)
                except Exception:
                    pass
            if self.state != "stopped":
                self.state = "stopped"

    def _do_send(self, iteration: int):
        """Send a message to all send channels."""
        msg = f"{self.config.message}_{iteration}"
        for ch in self.config.send_channels:
            if ch.send(msg):
                self.messages_sent += 1

    def _do_receive(self):
        """Receive a message from all receive channels."""
        for ch in self.config.recv_channels:
            data = ch.receive(timeout=0.5)
            if data is not None:
                self.messages_received += 1


class ProcessEngine:
    """Manages all simulated processes."""

    def __init__(self, logger: EventLogger):
        self.logger = logger
        self.processes: Dict[str, SimulatedProcess] = {}

    def add_process(self, config: ProcessConfig) -> SimulatedProcess:
        proc = SimulatedProcess(config, self.logger)
        self.processes[config.pid] = proc
        return proc

    def remove_process(self, pid: str):
        if pid in self.processes:
            self.processes[pid].stop()
            del self.processes[pid]

    def start_all(self):
        for proc in self.processes.values():
            if proc.state in ("idle", "stopped"):
                proc.start()

    def pause_all(self):
        for proc in self.processes.values():
            if proc.state == "running":
                proc.pause()

    def resume_all(self):
        for proc in self.processes.values():
            if proc.state == "paused":
                proc.resume()

    def stop_all(self):
        for proc in self.processes.values():
            proc.stop()

    def get_process(self, pid: str) -> Optional[SimulatedProcess]:
        return self.processes.get(pid)

    def get_all_states(self) -> Dict[str, str]:
        return {pid: p.state for pid, p in self.processes.items()}

    def reset(self):
        self.stop_all()
        self.processes.clear()
