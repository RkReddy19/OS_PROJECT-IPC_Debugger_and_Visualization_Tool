"""
Preset Scenarios — data-only scenario loaders for the IPC Debugger.
Each function returns (configs, connections, lock_setup) tuples.
Decoupled from GUI — pure data functions.
"""

from typing import List, Dict, Tuple, Optional, Callable
from utils.models import ProcessConfig


def load_normal_ipc():
    """Producer -> Consumer via queue.

    Returns:
        configs: dict of pid -> ProcessConfig
        connections: list of connection dicts
        lock_setup: None (no locks in this scenario)
    """
    configs = {}
    for pid, behavior, msg in [("Producer_A", "producer", "Ping"),
                                ("Consumer_B", "consumer", "")]:
        configs[pid] = ProcessConfig(
            pid=pid, priority=5, behavior=behavior,
            message=msg, delay=1.0,
        )

    connections = [{
        "source": "Producer_A",
        "dest": "Consumer_B",
        "channel_type": "queue",
        "channel_name": "A_to_B_queue",
    }]

    return configs, connections, None


def load_deadlock():
    """3-process circular deadlock scenario.

    Returns:
        configs: dict of pid -> ProcessConfig
        connections: list of visual connection dicts
        lock_setup: list of (pid, [lock_names_to_acquire])
    """
    configs = {}
    for pid in ["P1", "P2", "P3"]:
        configs[pid] = ProcessConfig(
            pid=pid, priority=5, behavior="producer_consumer",
            message="Data", delay=0.5,
        )

    connections = [
        {"source": "P1", "dest": "P2", "channel_type": "pipe",
         "channel_name": "Lock_A\u2192B"},
        {"source": "P2", "dest": "P3", "channel_type": "pipe",
         "channel_name": "Lock_B\u2192C"},
        {"source": "P3", "dest": "P1", "channel_type": "pipe",
         "channel_name": "Lock_C\u2192A"},
    ]

    # lock_setup: [(pid, [lock_name1, lock_name2]), ...]
    lock_setup = [
        ("P1", ["Lock_A", "Lock_B"]),
        ("P2", ["Lock_B", "Lock_C"]),
        ("P3", ["Lock_C", "Lock_A"]),
    ]

    return configs, connections, lock_setup


def load_bottleneck():
    """Fast producer / slow consumer bottleneck scenario.

    Returns:
        configs: dict of pid -> ProcessConfig
        connections: list of connection dicts (with maxsize kwarg)
        lock_setup: None
    """
    configs = {
        "FastSender": ProcessConfig(
            pid="FastSender", priority=9, behavior="producer",
            message="BulkData", delay=0.2,
        ),
        "SlowReceiver": ProcessConfig(
            pid="SlowReceiver", priority=2, behavior="consumer",
            message="", delay=3.0,
        ),
    }

    connections = [{
        "source": "FastSender",
        "dest": "SlowReceiver",
        "channel_type": "queue",
        "channel_name": "fast_slow_queue",
        "maxsize": 50,
    }]

    return configs, connections, None
