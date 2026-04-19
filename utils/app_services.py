"""
Application Services — Dependency Injection Container.
Centralizes creation and wiring of all core modules so the GUI
only depends on this single entry point.
"""

from typing import Dict, List, Optional

import tkinter as tk

from utils.event_logger import EventLogger
from utils.models import ProcessConfig
from engine.sync_manager import SynchronizationManager
from engine.process_engine import ProcessEngine
from analyzers.deadlock_detector import DeadlockDetector
from analyzers.bottleneck_detector import BottleneckDetector
from analyzers.race_detector import RaceConditionDetector
from analyzers.report_generator import ReportGenerator
from ipc.base import IPCChannel


class AppServices:
    """Dependency injection container for all core IPC Debugger services.

    Creates and holds canonical instances of every engine/analyzer module.
    The GUI should create one AppServices and pass references from it
    rather than constructing modules individually.
    """

    def __init__(self) -> None:
        # Core
        self.logger = EventLogger()
        self.sync_manager = SynchronizationManager(self.logger)
        self.process_engine = ProcessEngine(self.logger)

        # Analyzers
        self.deadlock_detector = DeadlockDetector(
            self.sync_manager, self.logger
        )
        self.bottleneck_detector = BottleneckDetector(self.logger)
        self.race_detector = RaceConditionDetector(self.logger)
        self.report_generator = ReportGenerator(self.logger)

    def reset_all(self) -> None:
        """Reset every service to its initial state."""
        self.process_engine.reset()
        self.sync_manager.reset()
        self.deadlock_detector.reset()
        self.race_detector.reset()
        self.logger.reset()
