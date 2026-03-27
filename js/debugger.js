/* =====================================================
   Debugger Module — Deadlock, Race, Bottleneck Detection
   ===================================================== */

class IPCDebugger {
    constructor() {
        this.alerts = [];
        this.deadlockHistory = [];
        this.raceConditionHistory = [];
        this.bottleneckHistory = [];
    }

    // ----- Deadlock Detection (Wait-For Graph Cycle Detection) -----

    buildWaitForGraph(processManager) {
        // Build adjacency list: process → process it's waiting for
        const graph = new Map();
        const processes = processManager.getAllProcesses();

        processes.forEach(p => {
            if (p.state !== 'terminated') {
                graph.set(p.id, []);
            }
        });

        // For each process waiting for a resource, find who holds that resource
        processes.forEach(p => {
            if (p.waitingForResource !== null) {
                // Find which process holds the resource this process is waiting for
                processes.forEach(other => {
                    if (other.id !== p.id && other.holdingResources.includes(p.waitingForResource)) {
                        if (graph.has(p.id)) {
                            graph.get(p.id).push(other.id);
                        }
                    }
                });
            }
        });

        return graph;
    }

    detectDeadlock(processManager) {
        const graph = this.buildWaitForGraph(processManager);
        const cycles = this.findCycles(graph);

        if (cycles.length > 0) {
            cycles.forEach(cycle => {
                const processNames = cycle.map(id => {
                    const p = processManager.getProcess(id);
                    return p ? p.name : `P${id}`;
                });

                const alert = {
                    type: 'critical',
                    category: 'deadlock',
                    title: '❌ DEADLOCK DETECTED',
                    message: `Circular wait: ${processNames.join(' → ')} → ${processNames[0]}`,
                    processes: cycle,
                    tick: window.app ? window.app.tick : 0
                };

                // Avoid duplicate alerts for same cycle
                const cycleKey = cycle.sort().join('-');
                if (!this.deadlockHistory.includes(cycleKey)) {
                    this.deadlockHistory.push(cycleKey);
                    this.addAlert(alert);

                    // Set processes to blocked
                    cycle.forEach(id => {
                        const p = processManager.getProcess(id);
                        if (p && p.state !== 'terminated') {
                            p.state = 'blocked';
                        }
                    });

                    if (window.app && window.app.logger) {
                        window.app.logger.log('SYS', '❌ DEADLOCK', `Processes: ${processNames.join(', ')}`, 'deadlock');
                    }
                }
            });
        }

        return cycles;
    }

    findCycles(graph) {
        const visited = new Set();
        const inStack = new Set();
        const cycles = [];

        const dfs = (node, path) => {
            visited.add(node);
            inStack.add(node);
            path.push(node);

            const neighbors = graph.get(node) || [];
            for (const neighbor of neighbors) {
                if (!visited.has(neighbor)) {
                    dfs(neighbor, [...path]);
                } else if (inStack.has(neighbor)) {
                    // Found a cycle
                    const cycleStart = path.indexOf(neighbor);
                    if (cycleStart !== -1) {
                        cycles.push(path.slice(cycleStart));
                    }
                }
            }

            inStack.delete(node);
        };

        for (const node of graph.keys()) {
            if (!visited.has(node)) {
                dfs(node, []);
            }
        }

        return cycles;
    }

    // ----- Race Condition Detection -----

    detectRaceConditions(sharedMemoryManager) {
        const allRaces = sharedMemoryManager.getAllRaceConditions();
        const newRaces = allRaces.filter(race => {
            const key = `${race.tick}-${race.key}`;
            if (this.raceConditionHistory.includes(key)) return false;
            this.raceConditionHistory.push(key);
            return true;
        });

        newRaces.forEach(race => {
            this.addAlert({
                type: 'warning',
                category: 'race_condition',
                title: '⚠ Race Condition',
                message: race.description,
                tick: race.tick
            });
        });

        return newRaces;
    }

    // ----- Bottleneck Detection -----

    detectBottlenecks(pipeManager, queueManager, processManager) {
        const bottlenecks = [];

        // Check pipe buffer utilization
        pipeManager.getAllPipes().forEach(pipe => {
            if (pipe.getUtilization() > 0.8) {
                const key = `pipe-${pipe.id}-${window.app ? window.app.tick : 0}`;
                if (!this.bottleneckHistory.includes(key)) {
                    this.bottleneckHistory.push(key);
                    const alert = {
                        type: 'warning',
                        category: 'bottleneck',
                        title: '⚠ Pipe Bottleneck',
                        message: `Pipe ${pipe.id} (${pipe.from.name}→${pipe.to.name}) buffer ${Math.round(pipe.getUtilization() * 100)}% full`,
                        tick: window.app ? window.app.tick : 0
                    };
                    bottlenecks.push(alert);
                    this.addAlert(alert);
                }
            }
        });

        // Check queue utilization & overflow
        queueManager.getAllQueues().forEach(queue => {
            if (queue.getUtilization() > 0.8) {
                const key = `queue-${queue.id}-${window.app ? window.app.tick : 0}`;
                if (!this.bottleneckHistory.includes(key)) {
                    this.bottleneckHistory.push(key);
                    const alert = {
                        type: queue.isFull() ? 'critical' : 'warning',
                        category: 'bottleneck',
                        title: queue.isFull() ? '❌ Queue Overflow' : '⚠ Queue Filling Up',
                        message: `Queue ${queue.id}: ${queue.queue.length}/${queue.maxCapacity} messages (overflow count: ${queue.overflowCount})`,
                        tick: window.app ? window.app.tick : 0
                    };
                    bottlenecks.push(alert);
                    this.addAlert(alert);
                }
            }
        });

        // Check for processes waiting too long
        processManager.getAllProcesses().forEach(p => {
            if (p.state === 'waiting' && p.waitingForResource) {
                const key = `wait-${p.id}-long`;
                if (!this.bottleneckHistory.includes(key)) {
                    this.bottleneckHistory.push(key);
                    const alert = {
                        type: 'info',
                        category: 'bottleneck',
                        title: 'ℹ Process Waiting',
                        message: `${p.name} waiting for resource: ${p.waitingForResource}`,
                        tick: window.app ? window.app.tick : 0
                    };
                    bottlenecks.push(alert);
                    this.addAlert(alert);
                }
            }
        });

        return bottlenecks;
    }

    // ----- Alert Management -----

    addAlert(alert) {
        alert.id = this.alerts.length;
        alert.timestamp = new Date().toLocaleTimeString('en-US', { hour12: false });
        this.alerts.push(alert);
        this.renderAlert(alert);
    }

    renderAlert(alert) {
        const container = document.getElementById('alert-list');
        if (!container) return;

        // Remove empty state if present
        const emptyState = container.querySelector('.empty-state');
        if (emptyState) emptyState.remove();

        const el = document.createElement('div');
        el.className = `alert-item ${alert.type}`;
        el.innerHTML = `
      <div class="alert-title">${alert.title}</div>
      <div>${alert.message}</div>
      <div class="alert-time">Tick ${alert.tick} • ${alert.timestamp}</div>
    `;
        container.insertBefore(el, container.firstChild);

        // Limit displayed alerts
        while (container.children.length > 50) {
            container.removeChild(container.lastChild);
        }
    }

    // ----- Run All Checks -----

    runAllChecks(processManager, pipeManager, queueManager, sharedMemoryManager) {
        const deadlocks = this.detectDeadlock(processManager);
        const races = this.detectRaceConditions(sharedMemoryManager);
        const bottlenecks = this.detectBottlenecks(pipeManager, queueManager, processManager);

        return {
            deadlocks: deadlocks.length,
            raceConditions: races.length,
            bottlenecks: bottlenecks.length
        };
    }

    clear() {
        this.alerts = [];
        this.deadlockHistory = [];
        this.raceConditionHistory = [];
        this.bottleneckHistory = [];

        const container = document.getElementById('alert-list');
        if (container) {
            container.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">🛡️</div>
          <p>No issues detected. Start a simulation to begin analysis.</p>
        </div>
      `;
        }
    }
}

window.IPCDebugger = IPCDebugger;
