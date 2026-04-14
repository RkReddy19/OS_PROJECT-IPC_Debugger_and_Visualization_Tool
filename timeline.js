/* =====================================================
   Timeline Module — Horizontal timeline view
   ===================================================== */

class Timeline {
    constructor() {
        this.data = new Map(); // processId → array of states per tick
        this.maxTicks = 60;
    }

    recordTick(processManager, tick) {
        processManager.getAllProcesses().forEach(p => {
            if (!this.data.has(p.id)) {
                this.data.set(p.id, []);
            }
            const timeline = this.data.get(p.id);
            // Map state to timeline block type
            let blockType = 'idle';
            switch (p.state) {
                case 'running': blockType = 'running'; break;
                case 'waiting': blockType = 'wait'; break;
                case 'blocked': blockType = 'blocked'; break;
                case 'terminated': blockType = 'idle'; break;
                case 'ready': blockType = 'running'; break;
            }
            timeline.push(blockType);

            // Keep only last maxTicks
            if (timeline.length > this.maxTicks) {
                timeline.shift();
            }
        });
    }

    // Override state for specific events
    recordEvent(processId, type) {
        if (!this.data.has(processId)) return;
        const timeline = this.data.get(processId);
        if (timeline.length > 0) {
            timeline[timeline.length - 1] = type; // send, receive, wait, blocked
        }
    }

    render(processManager, currentTick) {
        const container = document.getElementById('timeline-container');
        if (!container) return;

        let html = '';

        processManager.getAllProcesses().forEach(p => {
            const timeline = this.data.get(p.id) || [];
            html += `<div class="timeline-row">`;
            html += `<div class="timeline-label">${p.name}</div>`;
            html += `<div class="timeline-blocks">`;

            const startIdx = Math.max(0, timeline.length - this.maxTicks);
            for (let i = startIdx; i < timeline.length; i++) {
                const isCurrentTick = (i === timeline.length - 1);
                html += `<div class="timeline-block ${timeline[i]}${isCurrentTick ? ' current' : ''}" title="Tick ${i}: ${timeline[i]}"></div>`;
            }

            html += `</div></div>`;
        });

        // Legend
        html += `<div class="timeline-legend">
      <div class="legend-item"><div class="legend-color" style="background:var(--accent-indigo)"></div>Running</div>
      <div class="legend-item"><div class="legend-color" style="background:var(--accent-emerald)"></div>Send</div>
      <div class="legend-item"><div class="legend-color" style="background:var(--accent-cyan)"></div>Receive</div>
      <div class="legend-item"><div class="legend-color" style="background:var(--accent-amber)"></div>Wait</div>
      <div class="legend-item"><div class="legend-color" style="background:var(--accent-rose)"></div>Blocked</div>
    </div>`;

        container.innerHTML = html;
    }

    clear() {
        this.data.clear();
        const container = document.getElementById('timeline-container');
        if (container) container.innerHTML = '';
    }
}

window.Timeline = Timeline;
