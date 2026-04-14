/* =====================================================
   Visualizer Module — SVG-based process visualization
   ===================================================== */

class Visualizer {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.svg = null;
        this.width = 0;
        this.height = 0;
        this.particles = [];
        this.animationFrame = null;
        this.init();
    }

    init() {
        if (!this.canvas) return;
        this.resize();
        window.addEventListener('resize', () => this.resize());
    }

    resize() {
        if (!this.canvas) return;
        const rect = this.canvas.parentElement.getBoundingClientRect();
        this.width = rect.width;
        this.height = rect.height;
        this.canvas.setAttribute('width', this.width);
        this.canvas.setAttribute('height', this.height);
        this.canvas.setAttribute('viewBox', `0 0 ${this.width} ${this.height}`);
    }

    // Calculate positions for processes in a circular / smart layout
    calculateLayout(processes, connections) {
        const cx = this.width / 2;
        const cy = this.height / 2;
        const radius = Math.min(this.width, this.height) * 0.32;
        const count = processes.length;

        if (count === 0) return;

        if (count <= 2) {
            // Side by side
            processes.forEach((p, i) => {
                p.x = cx + (i === 0 ? -radius * 0.6 : radius * 0.6);
                p.y = cy;
            });
        } else {
            // Circular layout
            processes.forEach((p, i) => {
                const angle = (2 * Math.PI * i / count) - Math.PI / 2;
                p.x = cx + radius * Math.cos(angle);
                p.y = cy + radius * Math.sin(angle);
            });
        }
    }

    // Get color for process state
    getStateColor(state) {
        switch (state) {
            case 'running': return '#34d399';
            case 'ready': return '#6366f1';
            case 'waiting': return '#fbbf24';
            case 'blocked': return '#fb7185';
            case 'terminated': return '#64748b';
            default: return '#6366f1';
        }
    }

    getStateGlow(state) {
        switch (state) {
            case 'running': return 'rgba(52, 211, 153, 0.4)';
            case 'ready': return 'rgba(99, 102, 241, 0.4)';
            case 'waiting': return 'rgba(251, 191, 36, 0.4)';
            case 'blocked': return 'rgba(251, 113, 133, 0.5)';
            case 'terminated': return 'rgba(100, 116, 139, 0.2)';
            default: return 'rgba(99, 102, 241, 0.4)';
        }
    }

    getConnectionColor(type) {
        switch (type) {
            case 'pipe': return '#6366f1';
            case 'queue': return '#22d3ee';
            case 'shm': return '#a78bfa';
            default: return '#6366f1';
        }
    }

    getConnectionLabel(type) {
        switch (type) {
            case 'pipe': return 'PIPE';
            case 'queue': return 'QUEUE';
            case 'shm': return 'SHM';
            default: return type.toUpperCase();
        }
    }

    // Render everything
    render(processes, connections, deadlockCycles = []) {
        if (!this.canvas) return;
        this.resize();

        this.calculateLayout(processes, connections);

        let svg = '';

        // Defs for gradients and filters
        svg += `<defs>
      <filter id="glow">
        <feGaussianBlur stdDeviation="4" result="coloredBlur"/>
        <feMerge>
          <feMergeNode in="coloredBlur"/>
          <feMergeNode in="SourceGraphic"/>
        </feMerge>
      </filter>
      <filter id="glow-strong">
        <feGaussianBlur stdDeviation="8" result="coloredBlur"/>
        <feMerge>
          <feMergeNode in="coloredBlur"/>
          <feMergeNode in="SourceGraphic"/>
        </feMerge>
      </filter>
      <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto" fill="#94a3b8">
        <polygon points="0 0, 10 3.5, 0 7" />
      </marker>
    </defs>`;

        // Grid background
        svg += this.renderGrid();

        // Render connections first (behind nodes)
        connections.forEach(conn => {
            svg += this.renderConnection(conn, processes, deadlockCycles);
        });

        // Render data particles
        this.particles.forEach(particle => {
            svg += this.renderParticle(particle);
        });

        // Render process nodes on top
        processes.forEach(p => {
            const isInDeadlock = deadlockCycles.some(cycle => cycle.includes(p.id));
            svg += this.renderProcessNode(p, isInDeadlock);
        });

        // Empty state
        if (processes.length === 0) {
            svg += `<text x="${this.width / 2}" y="${this.height / 2 - 20}" text-anchor="middle" fill="#64748b" font-family="Inter" font-size="16" font-weight="600">No Processes</text>`;
            svg += `<text x="${this.width / 2}" y="${this.height / 2 + 10}" text-anchor="middle" fill="#475569" font-family="Inter" font-size="12">Select a scenario to begin simulation</text>`;
        }

        this.canvas.innerHTML = svg;
    }

    renderGrid() {
        let svg = '<g opacity="0.05">';
        const spacing = 30;
        for (let x = 0; x < this.width; x += spacing) {
            svg += `<line x1="${x}" y1="0" x2="${x}" y2="${this.height}" stroke="#94a3b8" stroke-width="0.5"/>`;
        }
        for (let y = 0; y < this.height; y += spacing) {
            svg += `<line x1="0" y1="${y}" x2="${this.width}" y2="${y}" stroke="#94a3b8" stroke-width="0.5"/>`;
        }
        svg += '</g>';
        return svg;
    }

    renderProcessNode(process, isInDeadlock) {
        const { x, y, name, state } = process;
        const color = this.getStateColor(state);
        const glow = this.getStateGlow(state);
        const nodeRadius = 30;

        let svg = `<g class="viz-process-node" transform="translate(${x}, ${y})">`;

        // Outer glow ring
        if (state !== 'terminated') {
            svg += `<circle r="${nodeRadius + 8}" fill="none" stroke="${glow}" stroke-width="2" opacity="0.5">`;
            if (state === 'blocked' || isInDeadlock) {
                svg += `<animate attributeName="r" values="${nodeRadius + 6};${nodeRadius + 14};${nodeRadius + 6}" dur="1.5s" repeatCount="indefinite"/>`;
                svg += `<animate attributeName="opacity" values="0.5;0.15;0.5" dur="1.5s" repeatCount="indefinite"/>`;
            } else if (state === 'running') {
                svg += `<animate attributeName="r" values="${nodeRadius + 6};${nodeRadius + 10};${nodeRadius + 6}" dur="2s" repeatCount="indefinite"/>`;
                svg += `<animate attributeName="opacity" values="0.4;0.15;0.4" dur="2s" repeatCount="indefinite"/>`;
            }
            svg += `</circle>`;
        }

        // Main circle
        const fillColor = isInDeadlock ? '#fb7185' : color;
        svg += `<circle class="viz-process-circle" r="${nodeRadius}" 
      fill="${fillColor}" fill-opacity="0.15" 
      stroke="${fillColor}" stroke-width="2.5"
      filter="url(#glow)"/>`;

        // Process name
        svg += `<text class="viz-process-label" y="-3">${name}</text>`;

        // State label below
        svg += `<text class="viz-process-state-label" y="14" fill="${color}">${isInDeadlock ? 'DEADLOCK' : state.toUpperCase()}</text>`;

        svg += `</g>`;
        return svg;
    }

    renderConnection(conn, processes, deadlockCycles) {
        const fromProcess = processes.find(p => p.id === conn.fromId);
        const toProcess = processes.find(p => p.id === conn.toId);

        if (!fromProcess || !toProcess) return '';

        const color = this.getConnectionColor(conn.type);
        const label = this.getConnectionLabel(conn.type);
        const nodeRadius = 30;

        // Calculate line endpoints (from edge of circles)
        const dx = toProcess.x - fromProcess.x;
        const dy = toProcess.y - fromProcess.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist === 0) return '';

        const nx = dx / dist;
        const ny = dy / dist;

        const x1 = fromProcess.x + nx * (nodeRadius + 10);
        const y1 = fromProcess.y + ny * (nodeRadius + 10);
        const x2 = toProcess.x - nx * (nodeRadius + 10);
        const y2 = toProcess.y - ny * (nodeRadius + 10);

        // Midpoint for label
        const mx = (x1 + x2) / 2;
        const my = (y1 + y2) / 2;

        // Curve control point (slight curve for visual appeal)
        const perpX = -ny * 20;
        const perpY = nx * 20;
        const cx = mx + perpX;
        const cy = my + perpY;

        let svg = '<g>';

        // Connection line
        const isActive = conn.isActive;
        svg += `<path d="M${x1},${y1} Q${cx},${cy} ${x2},${y2}" 
      class="viz-connection-line${isActive ? ' active' : ''}"
      stroke="${color}" stroke-opacity="${isActive ? 0.8 : 0.3}"
      marker-end="url(#arrowhead)"/>`;

        // IPC type label on the path
        const labelBgX = mx + perpX * 0.5;
        const labelBgY = my + perpY * 0.5;

        svg += `<rect x="${labelBgX - 22}" y="${labelBgY - 9}" width="44" height="18" rx="4" 
      fill="rgba(0,0,0,0.6)" stroke="${color}" stroke-width="1" stroke-opacity="0.5"/>`;
        svg += `<text class="viz-ipc-label" x="${labelBgX}" y="${labelBgY + 1}" fill="${color}">${label}</text>`;

        // Buffer / Queue indicator
        if (conn.utilization !== undefined) {
            const barWidth = 40;
            const barHeight = 4;
            const barX = labelBgX - barWidth / 2;
            const barY = labelBgY + 14;
            const fillWidth = barWidth * conn.utilization;

            svg += `<rect x="${barX}" y="${barY}" width="${barWidth}" height="${barHeight}" rx="2" fill="rgba(255,255,255,0.1)"/>`;
            svg += `<rect x="${barX}" y="${barY}" width="${fillWidth}" height="${barHeight}" rx="2" fill="${color}" opacity="0.7"/>`;
        }

        svg += '</g>';
        return svg;
    }

    renderParticle(particle) {
        return `<circle cx="${particle.x}" cy="${particle.y}" r="3" fill="${particle.color}" filter="url(#glow)">
      <animate attributeName="opacity" values="1;0.3;1" dur="0.8s" repeatCount="indefinite"/>
    </circle>`;
    }

    // Add animated particle along a connection path
    addDataParticle(fromProcess, toProcess, color) {
        const startX = fromProcess.x;
        const startY = fromProcess.y;
        const endX = toProcess.x;
        const endY = toProcess.y;

        const particle = {
            x: startX,
            y: startY,
            targetX: endX,
            targetY: endY,
            progress: 0,
            speed: 0.05,
            color: color || '#6366f1',
            alive: true
        };

        this.particles.push(particle);

        // Animate particle
        const animate = () => {
            particle.progress += particle.speed;
            if (particle.progress >= 1) {
                particle.alive = false;
                this.particles = this.particles.filter(p => p.alive);
                return;
            }
            particle.x = startX + (endX - startX) * particle.progress;
            particle.y = startY + (endY - startY) * particle.progress;
        };

        // Run animation steps
        const interval = setInterval(() => {
            animate();
            if (!particle.alive) {
                clearInterval(interval);
            }
        }, 50);
    }

    clear() {
        this.particles = [];
        if (this.canvas) {
            this.canvas.innerHTML = '';
        }
    }
}

window.Visualizer = Visualizer;
