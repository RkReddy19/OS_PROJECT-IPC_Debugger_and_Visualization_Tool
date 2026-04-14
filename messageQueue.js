/* =====================================================
   Message Queue IPC Module — Structured FIFO messaging
   ===================================================== */

class MessageQueue {
    constructor(id, maxCapacity = 8) {
        this.id = id;
        this.queue = [];
        this.maxCapacity = maxCapacity;
        this.type = 'queue';
        this.totalSent = 0;
        this.totalReceived = 0;
        this.producers = new Set(); // Process IDs that can send
        this.consumers = new Set(); // Process IDs that can receive
        this.overflowCount = 0;
    }

    send(fromProcess, data, priority = 0) {
        if (this.queue.length >= this.maxCapacity) {
            this.overflowCount++;
            if (window.app && window.app.logger) {
                window.app.logger.log(fromProcess.name, 'Queue OVERFLOW', `Queue ${this.id} full [${this.queue.length}/${this.maxCapacity}]`, 'blocked');
            }
            return { success: false, reason: 'queue_overflow' };
        }

        const message = {
            id: this.totalSent,
            from: fromProcess.name,
            data,
            priority,
            timestamp: window.app ? window.app.tick : 0
        };

        this.queue.push(message);
        // Sort by priority (higher first)
        this.queue.sort((a, b) => b.priority - a.priority);
        this.totalSent++;
        this.producers.add(fromProcess.id);

        if (window.app && window.app.logger) {
            window.app.logger.log(fromProcess.name, 'Sent to Queue', `"${data}" [${this.queue.length}/${this.maxCapacity}] prio:${priority}`, 'send');
        }

        return { success: true };
    }

    receive(toProcess) {
        if (this.queue.length === 0) {
            if (window.app && window.app.logger) {
                window.app.logger.log(toProcess.name, 'Queue EMPTY — waiting', `Queue ${this.id}`, 'wait');
            }
            return { success: false, reason: 'queue_empty' };
        }

        const message = this.queue.shift();
        this.totalReceived++;
        this.consumers.add(toProcess.id);

        if (window.app && window.app.logger) {
            window.app.logger.log(toProcess.name, 'Received from Queue', `"${message.data}" from ${message.from} [${this.queue.length}/${this.maxCapacity}]`, 'receive');
        }

        return { success: true, message };
    }

    getUtilization() {
        return this.queue.length / this.maxCapacity;
    }

    isFull() {
        return this.queue.length >= this.maxCapacity;
    }

    clear() {
        this.queue = [];
        this.totalSent = 0;
        this.totalReceived = 0;
        this.overflowCount = 0;
        this.producers.clear();
        this.consumers.clear();
    }
}

class MessageQueueManager {
    constructor() {
        this.queues = new Map();
        this.nextId = 1;
    }

    createQueue(maxCapacity = 8) {
        const id = this.nextId++;
        const queue = new MessageQueue(id, maxCapacity);
        this.queues.set(id, queue);
        return queue;
    }

    getQueue(id) {
        return this.queues.get(id);
    }

    getAllQueues() {
        return Array.from(this.queues.values());
    }

    clear() {
        this.queues.clear();
        this.nextId = 1;
    }
}

window.MessageQueue = MessageQueue;
window.MessageQueueManager = MessageQueueManager;
