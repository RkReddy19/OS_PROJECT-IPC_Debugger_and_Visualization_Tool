/* =====================================================
   Logger Module — Event logging and report export
   ===================================================== */

class Logger {
  constructor() {
    this.events = [];
    this.maxDisplayEvents = 200;
  }

  log(processId, action, detail, type = 'system') {
    const event = {
      id: this.events.length,
      tick: window.app ? window.app.tick : 0,
      timestamp: this.formatTime(),
      processId,
      action,
      detail,
      type // send, receive, wait, blocked, deadlock, system
    };
    this.events.push(event);
    this.renderEvent(event);
    return event;
  }

  formatTime() {
    const now = new Date();
    return now.toLocaleTimeString('en-US', { hour12: false }) + '.' + String(now.getMilliseconds()).padStart(3, '0');
  }

  renderEvent(event) {
    const container = document.getElementById('event-log');
    if (!container) return;

    const el = document.createElement('div');
    el.className = `event-entry ${event.type}`;
    el.innerHTML = `
      <span class="event-time">T${String(event.tick).padStart(3, '0')}</span>
      <span class="event-process">${event.processId || 'SYS'}</span>
      <span class="event-action">${event.action}${event.detail ? ' — ' + event.detail : ''}</span>
    `;

    container.appendChild(el);

    // Auto-scroll
    container.scrollTop = container.scrollHeight;

    // Limit displayed events
    while (container.children.length > this.maxDisplayEvents) {
      container.removeChild(container.firstChild);
    }
  }

  clear() {
    this.events = [];
    const container = document.getElementById('event-log');
    if (container) container.innerHTML = '';
  }

  getEventsByProcess(processId) {
    return this.events.filter(e => e.processId === processId);
  }

  getEventsByType(type) {
    return this.events.filter(e => e.type === type);
  }

  generateReport() {
    const totalMessages = this.events.filter(e => e.type === 'send').length;
    const deadlocks = this.events.filter(e => e.type === 'deadlock').length;
    const warnings = this.events.filter(e => e.type === 'blocked' || e.type === 'wait').length;

    const processIds = [...new Set(this.events.map(e => e.processId).filter(Boolean))];

    let report = `╔══════════════════════════════════════════╗\n`;
    report +=    `║       IPC DEBUGGER — DEBUG REPORT         ║\n`;
    report +=    `╚══════════════════════════════════════════╝\n\n`;
    report += `Generated: ${new Date().toLocaleString()}\n`;
    report += `Total Ticks: ${window.app ? window.app.tick : 0}\n\n`;

    report += `─── SUMMARY ───────────────────────────────\n`;
    report += `  Processes:          ${processIds.length}\n`;
    report += `  Total Events:       ${this.events.length}\n`;
    report += `  Messages Sent:      ${totalMessages}\n`;
    report += `  Messages Received:  ${this.events.filter(e => e.type === 'receive').length}\n`;
    report += `  Deadlocks Detected: ${deadlocks}\n`;
    report += `  Warnings:           ${warnings}\n\n`;

    report += `─── PROCESS DETAILS ───────────────────────\n`;
    processIds.forEach(pid => {
      const pEvents = this.getEventsByProcess(pid);
      report += `  ${pid}: ${pEvents.length} events\n`;
    });
    report += `\n`;

    report += `─── EVENT LOG ─────────────────────────────\n`;
    this.events.forEach(e => {
      report += `  [T${String(e.tick).padStart(3, '0')}] ${(e.processId || 'SYS').padEnd(4)} ${e.action}${e.detail ? ' — ' + e.detail : ''}\n`;
    });

    return report;
  }

  exportReport() {
    const report = this.generateReport();
    const blob = new Blob([report], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ipc_debug_report_${Date.now()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }
}

// Export
window.Logger = Logger;
