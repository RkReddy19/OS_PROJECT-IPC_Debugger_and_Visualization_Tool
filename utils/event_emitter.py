"""
EventEmitter Mixin — pub/sub event dispatching.
Eliminates duplicated callback management across modules.
"""

import logging
import threading
from typing import Dict, List, Callable

logger = logging.getLogger("ipc.emitter")


class EventEmitter:
    """Mixin providing pub/sub event dispatching.

    Usage:
        class MyModule(EventEmitter):
            def __init__(self):
                super().__init__()

            def do_something(self):
                self.emit('something_happened', data=42)

        module = MyModule()
        module.on('something_happened', lambda data: print(data))
    """

    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}
        self._emitter_lock = threading.Lock()

    def on(self, event: str, callback: Callable) -> None:
        """Register a listener for an event type."""
        with self._emitter_lock:
            if event not in self._listeners:
                self._listeners[event] = []
            self._listeners[event].append(callback)

    def off(self, event: str, callback: Callable) -> None:
        """Remove a listener."""
        with self._emitter_lock:
            if event in self._listeners:
                self._listeners[event] = [
                    cb for cb in self._listeners[event] if cb != callback
                ]

    def emit(self, event: str, *args, **kwargs) -> None:
        """Fire all listeners for an event. Errors logged, never silenced."""
        with self._emitter_lock:
            listeners = list(self._listeners.get(event, []))
        for cb in listeners:
            try:
                cb(*args, **kwargs)
            except Exception as e:
                logger.warning(
                    "EventEmitter callback error on '%s': %s", event, e
                )
