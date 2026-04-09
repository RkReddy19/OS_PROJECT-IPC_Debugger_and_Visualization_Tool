"""
Deadlock Detection Engine — Wait-For Graph construction and cycle detection.
Enhancement: detects ALL cycles, not just the first one.
"""

import networkx as nx
from typing import List, Tuple

from engine.sync_manager import SynchronizationManager
from utils.event_logger import EventLogger


class DeadlockDetector:
    """Builds a Wait-For Graph and detects ALL cycles (deadlocks)."""

    def __init__(self, sync_manager: SynchronizationManager, logger: EventLogger):
        self.sync_manager = sync_manager
        self.logger = logger
        self.wfg = nx.DiGraph()
        self.last_cycles: List[List[str]] = []  # All detected cycles

    def build_wait_for_graph(self, process_ids: List[str]) -> nx.DiGraph:
        """Construct a Wait-For Graph from the current synchronization state.
        Nodes  = active process IDs
        Edges  = (waiter -> holder) meaning 'waiter is blocked by holder'"""
        self.wfg.clear()
        for pid in process_ids:
            self.wfg.add_node(pid)
        edges = self.sync_manager.get_wait_for_edges()
        for waiter, holder in edges:
            if waiter in process_ids and holder in process_ids:
                self.wfg.add_edge(waiter, holder)
        return self.wfg

    def detect_deadlock(self, process_ids: List[str]) -> List[Tuple[str, str]]:
        """Detect ALL deadlocks by finding every cycle in the Wait-For Graph.

        Returns:
            List of (waiter, holder) edges forming deadlock cycles.
            Empty list if no deadlock.
        """
        self.build_wait_for_graph(process_ids)

        # Find ALL cycles using nx.simple_cycles
        all_cycles = list(nx.simple_cycles(self.wfg))

        if all_cycles:
            self.last_cycles = all_cycles
            # Collect all edges from all cycles
            all_cycle_edges = []
            all_involved = set()
            for cycle in all_cycles:
                for i in range(len(cycle)):
                    u = cycle[i]
                    v = cycle[(i + 1) % len(cycle)]
                    all_cycle_edges.append((u, v))
                    all_involved.add(u)
                    all_involved.add(v)

            # Log each cycle
            for cycle in all_cycles:
                cycle_str = " -> ".join(cycle + [cycle[0]])
                self.logger.log_event(
                    source_pid="SYSTEM", dest_pid="",
                    action="DEADLOCK",
                    details=f"Cycle: {cycle_str} | Processes: {', '.join(cycle)}"
                )

            return all_cycle_edges
        else:
            self.last_cycles = []
            return []

    def get_involved_processes(self) -> List[str]:
        """Return all process IDs involved in any detected cycle."""
        involved = set()
        for cycle in self.last_cycles:
            involved.update(cycle)
        return list(involved)

    def find_cycle_dfs_manual(self) -> List[Tuple[str, str]]:
        """Manual DFS cycle detection (educational, finds ALL cycles).

        Uses the 3-color marking approach:
            WHITE (0) = not visited
            GRAY  (1) = in current DFS stack
            BLACK (2) = fully explored
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node: WHITE for node in self.wfg.nodes}
        parent = {node: None for node in self.wfg.nodes}
        all_cycle_edges = []

        def dfs(u):
            color[u] = GRAY
            for v in self.wfg.successors(u):
                if color[v] == GRAY:
                    # Back edge — cycle detected
                    cycle = [(u, v)]
                    current = u
                    while current != v:
                        p = parent.get(current)
                        if p is None:
                            break
                        cycle.append((p, current))
                        current = p
                    cycle.reverse()
                    all_cycle_edges.extend(cycle)
                elif color[v] == WHITE:
                    parent[v] = u
                    dfs(v)
            color[u] = BLACK

        for node in self.wfg.nodes:
            if color[node] == WHITE:
                dfs(node)
        return all_cycle_edges

    def get_graph_data(self) -> dict:
        """Return graph data for visualization."""
        return {
            "nodes": list(self.wfg.nodes),
            "edges": list(self.wfg.edges),
            "has_cycle": len(self.last_cycles) > 0,
            "cycle_nodes": self.get_involved_processes(),
            "num_cycles": len(self.last_cycles),
        }

    def reset(self):
        self.wfg.clear()
        self.last_cycles = []
