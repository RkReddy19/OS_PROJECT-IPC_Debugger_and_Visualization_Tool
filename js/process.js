/* =====================================================
   Process Simulator Module
   ===================================================== */

class Process {
    constructor(id, name) {
        this.id = id;
        this.name = name || `P${id}`;
        this.state = 'ready'; // ready, running, waiting, blocked, terminated
        this.messageInbox = [];
        this.holdingResources = [];  // Resources this process holds
        this.waitingForResource = null; // Resource this process is waiting for
        this.color = Process.COLORS[id % Process.COLORS.length];
        this.x = 0;
        this.y = 0;
    }

    static COLORS = [
        '#6366f1', '#22d3ee', '#34d399', '#fbbf24',
        '#fb7185', '#a78bfa', '#f97316', '#14b8a6'
    ];

    setState(newState) {
        const oldState = this.state;
        this.state = newState;
        if (window.app && window.app.logger) {
            window.app.logger.log(this.name, `State: ${oldState} → ${newState}`, null,
                newState === 'blocked' ? 'blocked' : newState === 'waiting' ? 'wait' : 'system');
        }
    }

    holdResource(resourceId) {
        if (!this.holdingResources.includes(resourceId)) {
            this.holdingResources.push(resourceId);
        }
    }

    releaseResource(resourceId) {
        this.holdingResources = this.holdingResources.filter(r => r !== resourceId);
    }

    waitFor(resourceId) {
        this.waitingForResource = resourceId;
        this.setState('waiting');
    }

    unblock() {
        this.waitingForResource = null;
        this.setState('running');
    }
}

class ProcessManager {
    constructor() {
        this.processes = new Map();
        this.nextId = 1;
    }

    createProcess(name) {
        const id = this.nextId++;
        const process = new Process(id, name || `P${id}`);
        this.processes.set(id, process);
        return process;
    }

    removeProcess(id) {
        const process = this.processes.get(id);
        if (process) {
            process.setState('terminated');
            // Don't delete, keep for history
        }
    }

    getProcess(id) {
        return this.processes.get(id);
    }

    getProcessByName(name) {
        for (const p of this.processes.values()) {
            if (p.name === name) return p;
        }
        return null;
    }

    getAllProcesses() {
        return Array.from(this.processes.values());
    }

    getActiveProcesses() {
        return this.getAllProcesses().filter(p => p.state !== 'terminated');
    }

    clear() {
        this.processes.clear();
        this.nextId = 1;
    }

    renderProcessList() {
        const container = document.getElementById('process-list');
        if (!container) return;

        container.innerHTML = '';
        this.getAllProcesses().forEach(p => {
            const el = document.createElement('div');
            el.className = 'process-item';
            el.dataset.processId = p.id;
            el.innerHTML = `
        <span class="state-dot ${p.state}"></span>
        <span class="process-name">${p.name}</span>
        <span class="process-state ${p.state}">${p.state}</span>
      `;
            container.appendChild(el);
        });
    }
}

// Export
window.Process = Process;
window.ProcessManager = ProcessManager;
