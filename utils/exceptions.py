"""
Custom Exception Classes for the IPC Debugger.
Provides granular exception handling for process engine, channels, and locks.
"""


class IPCDebuggerError(Exception):
    """Base exception for all IPC Debugger errors."""
    pass


class ProcessException(IPCDebuggerError):
    """Base class for process-related exceptions."""
    pass


class LockTimeoutException(ProcessException):
    """Lock acquisition timed out — may indicate deadlock."""
    pass


class ChannelException(ProcessException):
    """Channel operation failed (e.g., full/empty/closed channel)."""
    pass


class ChannelFullException(ChannelException):
    """Send failed because the channel is full."""
    pass


class ChannelClosedException(ChannelException):
    """Operation attempted on a closed channel."""
    pass


class SimulationError(IPCDebuggerError):
    """Error during simulation lifecycle (start/stop/reset)."""
    pass


class ConfigurationError(IPCDebuggerError):
    """Invalid or missing configuration."""
    pass
