"""
Report Generator — produces HTML, CSV, and text reports
with actionable recommendations based on analysis results.
"""

import csv
import io
import time
from datetime import datetime
from typing import List, Optional

from utils.models import BottleneckReport, ChannelMetrics, LogEvent, RaceReport
from utils.event_logger import EventLogger


class ReportGenerator:
    """Generates comprehensive analysis reports in multiple formats."""

    def __init__(self, logger: EventLogger):
        self.logger = logger

    # ════════════════════════════════════════════
    # RECOMMENDATIONS ENGINE
    # ════════════════════════════════════════════

    def generate_recommendations(
        self,
        bottlenecks: List[BottleneckReport],
        deadlock_cycles: list,
        race_reports: List[RaceReport],
        metrics: List[ChannelMetrics],
    ) -> List[str]:
        """Generate actionable optimization recommendations."""
        recs = []

        # Bottleneck recommendations
        for b in bottlenecks:
            if b.metric == "queue_depth":
                recs.append(
                    f"🔧 QUEUE OVERLOAD on '{b.channel_name}': "
                    f"Queue depth is {b.value:.0f}. "
                    f"Increase consumer speed, add more consumers, or increase queue capacity."
                )
            elif b.metric == "latency":
                recs.append(
                    f"🔧 HIGH LATENCY on '{b.channel_name}': "
                    f"Avg latency is {b.value:.3f}s. "
                    f"Consider reducing producer rate or using shared memory for lower latency."
                )
            elif b.metric == "throughput_ratio":
                recs.append(
                    f"🔧 THROUGHPUT MISMATCH on '{b.channel_name}': "
                    f"Send/Receive ratio is {b.value:.2f}. "
                    f"Possible message loss or underperforming consumer."
                )

        # Deadlock recommendations
        if deadlock_cycles:
            n = len(deadlock_cycles) if isinstance(deadlock_cycles[0], list) else 1
            recs.append(
                f"🔴 DEADLOCK DETECTED ({n} cycle(s)): "
                f"Enforce a global lock ordering to prevent circular waits. "
                f"Consider using timeout-based lock acquisition."
            )

        # Race condition recommendations
        for r in race_reports:
            recs.append(
                f"⚡ RACE CONDITION on '{r.resource_name}': "
                f"{r.access_type} by {', '.join(r.accessor_pids)}. "
                f"Add mutual exclusion (locks/semaphores) around shared resource access."
            )

        # General performance recommendations from metrics
        for m in metrics:
            if m.throughput > 0 and m.avg_latency > 1.0:
                recs.append(
                    f"📊 PERFORMANCE: '{m.name}' has high latency ({m.avg_latency:.3f}s) "
                    f"despite throughput of {m.throughput:.1f} msg/s. "
                    f"Consider switching to pipe or shared memory for lower overhead."
                )
            if m.channel_type == "queue" and m.peak_depth > m.max_queue_size * 0.8:
                recs.append(
                    f"📊 CAPACITY WARNING: '{m.name}' peak depth ({m.peak_depth}) "
                    f"is near max capacity ({m.max_queue_size}). "
                    f"Risk of message drops under load."
                )

        if not recs:
            recs.append("✅ No issues detected. System appears healthy.")

        return recs

    # ════════════════════════════════════════════
    # HTML REPORT
    # ════════════════════════════════════════════

    def generate_html_report(
        self,
        metrics: List[ChannelMetrics],
        bottlenecks: List[BottleneckReport],
        deadlock_cycles: list,
        race_reports: List[RaceReport],
        events: Optional[List[LogEvent]] = None,
    ) -> str:
        """Generate a styled HTML report."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        recs = self.generate_recommendations(
            bottlenecks, deadlock_cycles, race_reports, metrics
        )

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>IPC Debugger — Analysis Report</title>
<style>
  :root {{
    --bg: #0f172a;
    --panel: #1e293b;
    --card: #334155;
    --text: #e2e8f0;
    --muted: #94a3b8;
    --accent: #38bdf8;
    --ok: #22c55e;
    --warn: #f59e0b;
    --err: #ef4444;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: var(--bg);
    color: var(--text);
    font-family: 'Segoe UI', system-ui, sans-serif;
    padding: 32px;
    line-height: 1.6;
  }}
  h1 {{
    color: var(--accent);
    font-size: 28px;
    margin-bottom: 8px;
  }}
  h2 {{
    color: var(--accent);
    font-size: 20px;
    margin: 32px 0 16px 0;
    padding-bottom: 8px;
    border-bottom: 2px solid var(--card);
  }}
  .subtitle {{
    color: var(--muted);
    font-size: 14px;
    margin-bottom: 24px;
  }}
  .summary-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 32px;
  }}
  .summary-card {{
    background: var(--panel);
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    border: 1px solid var(--card);
  }}
  .summary-card .value {{
    font-size: 36px;
    font-weight: 700;
    color: var(--accent);
  }}
  .summary-card .label {{
    font-size: 13px;
    color: var(--muted);
    margin-top: 4px;
  }}
  .summary-card.danger .value {{ color: var(--err); }}
  .summary-card.warning .value {{ color: var(--warn); }}
  .summary-card.success .value {{ color: var(--ok); }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 16px 0;
    background: var(--panel);
    border-radius: 8px;
    overflow: hidden;
  }}
  th {{
    background: var(--card);
    color: var(--accent);
    padding: 12px 16px;
    text-align: left;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}
  td {{
    padding: 10px 16px;
    border-bottom: 1px solid var(--card);
    font-size: 14px;
  }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: rgba(56, 189, 248, 0.05); }}
  .severity {{
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
  }}
  .severity.CRITICAL {{ background: var(--err); color: #fff; }}
  .severity.HIGH {{ background: #dc2626; color: #fff; }}
  .severity.MEDIUM {{ background: var(--warn); color: #000; }}
  .severity.LOW {{ background: var(--muted); color: #000; }}
  .rec-list {{
    list-style: none;
    padding: 0;
  }}
  .rec-list li {{
    background: var(--panel);
    padding: 14px 18px;
    margin: 8px 0;
    border-radius: 8px;
    border-left: 4px solid var(--accent);
    font-size: 14px;
    line-height: 1.5;
  }}
  .footer {{
    margin-top: 40px;
    padding-top: 16px;
    border-top: 1px solid var(--card);
    color: var(--muted);
    font-size: 12px;
    text-align: center;
  }}
</style>
</head>
<body>
<h1>🔬 IPC Debugger — Analysis Report</h1>
<p class="subtitle">Generated on {timestamp}</p>
"""

        # Summary cards
        total_sent = sum(m.messages_sent for m in metrics)
        total_recv = sum(m.messages_received for m in metrics)
        n_bottlenecks = len(bottlenecks)
        n_deadlocks = len(deadlock_cycles) if deadlock_cycles else 0
        n_races = len(race_reports)

        html += '<div class="summary-grid">\n'
        html += f'  <div class="summary-card"><div class="value">{len(metrics)}</div><div class="label">Channels</div></div>\n'
        html += f'  <div class="summary-card success"><div class="value">{total_sent}</div><div class="label">Messages Sent</div></div>\n'
        html += f'  <div class="summary-card success"><div class="value">{total_recv}</div><div class="label">Messages Received</div></div>\n'
        dl_class = "danger" if n_deadlocks else "success"
        html += f'  <div class="summary-card {dl_class}"><div class="value">{n_deadlocks}</div><div class="label">Deadlocks</div></div>\n'
        bn_class = "warning" if n_bottlenecks else "success"
        html += f'  <div class="summary-card {bn_class}"><div class="value">{n_bottlenecks}</div><div class="label">Bottlenecks</div></div>\n'
        rc_class = "danger" if n_races else "success"
        html += f'  <div class="summary-card {rc_class}"><div class="value">{n_races}</div><div class="label">Race Conditions</div></div>\n'
        html += '</div>\n'

        # Channel Metrics Table
        html += '<h2>📊 Channel Metrics</h2>\n'
        if metrics:
            html += '<table>\n<tr>'
            html += '<th>Channel</th><th>Type</th><th>Source → Dest</th>'
            html += '<th>Sent</th><th>Received</th><th>Bytes</th>'
            html += '<th>Avg Latency</th><th>Throughput</th><th>Queue Depth</th>'
            html += '</tr>\n'
            for m in metrics:
                html += f'<tr>'
                html += f'<td>{m.name}</td><td>{m.channel_type}</td>'
                html += f'<td>{m.source} → {m.dest}</td>'
                html += f'<td>{m.messages_sent}</td><td>{m.messages_received}</td>'
                html += f'<td>{m.total_bytes}</td>'
                html += f'<td>{m.avg_latency:.4f}s</td>'
                html += f'<td>{m.throughput:.1f} msg/s</td>'
                html += f'<td>{m.queue_depth} / {m.peak_depth} peak</td>'
                html += f'</tr>\n'
            html += '</table>\n'
        else:
            html += '<p style="color:var(--muted)">No channel data available.</p>\n'

        # Bottlenecks
        html += '<h2>⚠️ Bottleneck Analysis</h2>\n'
        if bottlenecks:
            html += '<table>\n<tr><th>Channel</th><th>Severity</th><th>Metric</th><th>Value</th><th>Details</th></tr>\n'
            for b in bottlenecks:
                html += f'<tr><td>{b.channel_name}</td>'
                html += f'<td><span class="severity {b.severity}">{b.severity}</span></td>'
                html += f'<td>{b.metric}</td><td>{b.value:.2f}</td>'
                html += f'<td>{b.details}</td></tr>\n'
            html += '</table>\n'
        else:
            html += '<p style="color:var(--ok)">✅ No bottlenecks detected.</p>\n'

        # Deadlocks
        html += '<h2>🔴 Deadlock Analysis</h2>\n'
        if deadlock_cycles:
            for i, cycle in enumerate(deadlock_cycles):
                if isinstance(cycle, list):
                    cycle_str = " → ".join(cycle + [cycle[0]])
                    html += f'<p>Cycle {i+1}: <strong>{cycle_str}</strong></p>\n'
                else:
                    html += f'<p>Edge: {cycle}</p>\n'
        else:
            html += '<p style="color:var(--ok)">✅ No deadlocks detected.</p>\n'

        # Race Conditions
        html += '<h2>⚡ Race Condition Analysis</h2>\n'
        if race_reports:
            html += '<table>\n<tr><th>Resource</th><th>Type</th><th>Processes</th><th>Details</th></tr>\n'
            for r in race_reports:
                html += f'<tr><td>{r.resource_name}</td><td>{r.access_type}</td>'
                html += f'<td>{", ".join(r.accessor_pids)}</td>'
                html += f'<td>{r.details}</td></tr>\n'
            html += '</table>\n'
        else:
            html += '<p style="color:var(--ok)">✅ No race conditions detected.</p>\n'

        # Recommendations
        html += '<h2>💡 Recommendations</h2>\n'
        html += '<ul class="rec-list">\n'
        for rec in recs:
            html += f'  <li>{rec}</li>\n'
        html += '</ul>\n'

        # Event Log (last 100)
        if events:
            html += '<h2>📝 Recent Event Log</h2>\n'
            html += '<table>\n<tr><th>Time</th><th>Source</th><th>Action</th><th>Details</th></tr>\n'
            for e in events[-100:]:
                html += f'<tr><td>{e.timestamp:.3f}s</td>'
                html += f'<td>{e.source_pid}</td>'
                html += f'<td>{e.action}</td>'
                html += f'<td>{e.details}</td></tr>\n'
            html += '</table>\n'

        html += f"""
<div class="footer">
  IPC Debugger &amp; Visualization Tool — Report generated on {timestamp}
</div>
</body>
</html>"""
        return html

    # ════════════════════════════════════════════
    # CSV REPORT
    # ════════════════════════════════════════════

    def generate_csv_metrics(self, metrics: List[ChannelMetrics]) -> str:
        """Generate CSV of channel metrics."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Channel", "Type", "Source", "Dest",
            "Sent", "Received", "Bytes",
            "Avg Latency (s)", "Max Latency (s)",
            "Throughput (msg/s)", "Queue Depth", "Peak Depth"
        ])
        for m in metrics:
            writer.writerow([
                m.name, m.channel_type, m.source, m.dest,
                m.messages_sent, m.messages_received, m.total_bytes,
                f"{m.avg_latency:.4f}", f"{m.max_latency:.4f}",
                f"{m.throughput:.2f}", m.queue_depth, m.peak_depth,
            ])
        return output.getvalue()

    # ════════════════════════════════════════════
    # TEXT SUMMARY
    # ════════════════════════════════════════════

    def generate_text_summary(
        self,
        metrics: List[ChannelMetrics],
        bottlenecks: List[BottleneckReport],
        deadlock_cycles: list,
        race_reports: List[RaceReport],
    ) -> str:
        """Generate a plain-text summary report."""
        lines = []
        lines.append("=" * 60)
        lines.append("  IPC Debugger — Analysis Summary Report")
        lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 60)
        lines.append("")

        # Metrics
        lines.append("📊 CHANNEL METRICS")
        lines.append("-" * 40)
        for m in metrics:
            lines.append(f"  {m.name} ({m.channel_type}): {m.source} → {m.dest}")
            lines.append(f"    Sent={m.messages_sent}  Received={m.messages_received}  Bytes={m.total_bytes}")
            lines.append(f"    Latency: avg={m.avg_latency:.4f}s  max={m.max_latency:.4f}s")
            lines.append(f"    Throughput: {m.throughput:.2f} msg/s")
            if m.channel_type == "queue":
                lines.append(f"    Queue: depth={m.queue_depth}  peak={m.peak_depth}  max={m.max_queue_size}")
            lines.append("")

        # Issues
        lines.append("⚠️ ISSUES DETECTED")
        lines.append("-" * 40)
        if not bottlenecks and not deadlock_cycles and not race_reports:
            lines.append("  ✅ No issues detected.")
        for b in bottlenecks:
            lines.append(f"  [{b.severity}] Bottleneck: {b.channel_name} — {b.details}")
        if deadlock_cycles:
            lines.append(f"  [CRITICAL] Deadlock: {len(deadlock_cycles)} cycle(s) detected")
        for r in race_reports:
            lines.append(f"  [HIGH] Race: {r.resource_name} — {r.details}")
        lines.append("")

        # Recommendations
        recs = self.generate_recommendations(
            bottlenecks, deadlock_cycles, race_reports, metrics
        )
        lines.append("💡 RECOMMENDATIONS")
        lines.append("-" * 40)
        for rec in recs:
            lines.append(f"  {rec}")
        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)
