"""
Bottleneck Detection Module — analyzes IPC channels for performance issues.
FIX: FIFO-based latency pairing instead of naive index match (Issue #4).
"""

from collections import deque
from typing import List

from utils.models import BottleneckReport, ChannelMetrics
from utils.event_logger import EventLogger
from ipc.base import IPCChannel
from ipc.queue_channel import QueueChannel


class BottleneckDetector:
    """Analyzes IPC channels to identify performance bottlenecks."""

    def __init__(self, logger: EventLogger):
        self.logger = logger
        self.queue_depth_threshold = 10
        self.latency_threshold = 2.0
        self.throughput_ratio_threshold = 0.5

    def analyze_channels(self, channels: List[IPCChannel]) -> List[BottleneckReport]:
        """Run bottleneck analysis on all registered channels."""
        reports = []

        for ch in channels:
            # --- Queue depth analysis ---
            if isinstance(ch, QueueChannel):
                depth = ch.queue_depth
                peak = ch.peak_depth
                if depth > self.queue_depth_threshold:
                    severity = "CRITICAL" if depth > self.queue_depth_threshold * 2 else "HIGH"
                    reports.append(BottleneckReport(
                        ch.name, ch.channel_type, severity,
                        "queue_depth", float(depth),
                        f"Queue depth {depth} (peak: {peak}) exceeds threshold "
                        f"{self.queue_depth_threshold}. Consumer '{ch.dest_pid}' may be too slow."
                    ))

            # --- Latency analysis (FIFO pairing fix) ---
            latencies = self._compute_latencies_fifo(ch)
            if latencies:
                avg_latency = sum(latencies) / len(latencies)
                if avg_latency > self.latency_threshold:
                    severity = "HIGH" if avg_latency > self.latency_threshold * 2 else "MEDIUM"
                    reports.append(BottleneckReport(
                        ch.name, ch.channel_type, severity,
                        "latency", avg_latency,
                        f"Avg latency {avg_latency:.3f}s exceeds threshold "
                        f"{self.latency_threshold}s."
                    ))

            # --- Throughput ratio (recv/send) ---
            if ch.message_count > 0:
                sent = len(ch.send_times)
                received = len(ch.receive_times)
                if sent > 0:
                    ratio = received / sent
                    if ratio < self.throughput_ratio_threshold:
                        reports.append(BottleneckReport(
                            ch.name, ch.channel_type, "MEDIUM",
                            "throughput_ratio", ratio,
                            f"Only {received}/{sent} messages received "
                            f"(ratio={ratio:.2f}). Possible message loss or slow consumer."
                        ))

        # Log findings
        for report in reports:
            self.logger.log_event(
                source_pid="SYSTEM", dest_pid="",
                action="BOTTLENECK", details=str(report)
            )
        return reports

    def _compute_latencies_fifo(self, ch: IPCChannel) -> List[float]:
        """FIFO-based latency calculation (Issue #4 fix).

        Uses a deque of unmatched send times. Each receive pops the
        oldest send, correctly handling the FIFO ordering of messages."""
        if not ch.send_times or not ch.receive_times:
            return []

        send_queue = deque(sorted(ch.send_times))
        latencies = []
        for recv_time in sorted(ch.receive_times):
            if send_queue and recv_time >= send_queue[0]:
                send_time = send_queue.popleft()
                lat = recv_time - send_time
                if lat > 0:
                    latencies.append(lat)
        return latencies

    def get_channel_metrics(self, channels: List[IPCChannel]) -> List[ChannelMetrics]:
        """Compute per-channel metrics for visualization."""
        metrics = []
        for ch in channels:
            latencies = self._compute_latencies_fifo(ch)
            avg_lat = sum(latencies) / len(latencies) if latencies else 0
            max_lat = max(latencies) if latencies else 0

            # Queue-specific
            q_depth = 0
            q_max = 0
            q_peak = 0
            if isinstance(ch, QueueChannel):
                q_depth = ch.queue_depth
                q_max = ch.maxsize
                q_peak = ch.peak_depth

            # Throughput
            throughput = 0.0
            if ch.send_times and len(ch.send_times) >= 2:
                duration = ch.send_times[-1] - ch.send_times[0]
                throughput = len(ch.send_times) / duration if duration > 0 else 0

            metrics.append(ChannelMetrics(
                name=ch.name,
                channel_type=ch.channel_type,
                source=ch.source_pid,
                dest=ch.dest_pid,
                messages_sent=len(ch.send_times),
                messages_received=len(ch.receive_times),
                total_bytes=ch.total_bytes,
                avg_latency=avg_lat,
                max_latency=max_lat,
                queue_depth=q_depth,
                max_queue_size=q_max,
                peak_depth=q_peak,
                throughput=throughput,
            ))
        return metrics
