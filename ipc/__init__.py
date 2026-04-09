"""
IPC Module — channel implementations and factory function.
"""

from ipc.base import IPCChannel
from ipc.pipe_channel import PipeChannel
from ipc.queue_channel import QueueChannel
from ipc.shared_memory_channel import SharedMemoryChannel
from utils.event_logger import EventLogger


def create_channel(channel_type: str, name: str, source_pid: str,
                   dest_pid: str, logger: EventLogger,
                   race_detector=None, **kwargs) -> IPCChannel:
    """Factory: create the right IPC channel by type string."""
    channel_type = channel_type.lower().replace(" ", "_")
    if channel_type == "pipe":
        return PipeChannel(name, source_pid, dest_pid, logger,
                           race_detector=race_detector)
    elif channel_type == "queue":
        return QueueChannel(name, source_pid, dest_pid, logger,
                            race_detector=race_detector, **kwargs)
    elif channel_type in ("shared_memory", "sharedmemory"):
        return SharedMemoryChannel(name, source_pid, dest_pid, logger,
                                   race_detector=race_detector)
    else:
        raise ValueError(f"Unknown channel type: {channel_type}")


__all__ = [
    "IPCChannel", "PipeChannel", "QueueChannel", "SharedMemoryChannel",
    "create_channel",
]
