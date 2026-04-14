/* =====================================================
   Pipe IPC Module — Unidirectional communication channel
   ===================================================== */

class Pipe {
    constructor(id, fromProcess, toProcess, bufferSize = 5) {
        this.id = id;
        this.from = fromProcess; // Process object
        this.to = toProcess;     // Process object
        this.buffer = [];
        this.bufferSize = bufferSize;
        this.type = 'pipe';
        this.totalWritten = 0;
        this.totalRead = 0;
        this.isActive = false;
    }

    write(data) {
        if (this.buffer.length >= this.bufferSize) {
            if (window.app && window.app.logger) {
                window.app.logger.log(this.from.name, 'Pipe FULL — cannot write', `Pipe ${this.id}`, 'blocked');
            }
            return { success: false, reason: 'buffer_full' };
        }

        this.buffer.push({
            data,
            timestamp: window.app ? window.app.tick : 0
        });
        this.totalWritten++;
        this.isActive = true;

        if (window.app && window.app.logger) {
            window.app.logger.log(this.from.name, `Wrote to Pipe`, `"${data}" → ${this.to.name} [${this.buffer.length}/${this.bufferSize}]`, 'send');
        }

        return { success: true };
    }

    read() {
        if (this.buffer.length === 0) {
            if (window.app && window.app.logger) {
                window.app.logger.log(this.to.name, 'Pipe EMPTY — waiting', `Pipe ${this.id}`, 'wait');
            }
            return { success: false, reason: 'buffer_empty' };
        }

        const msg = this.buffer.shift();
        this.totalRead++;

        if (this.buffer.length === 0) {
            this.isActive = false;
        }

        if (window.app && window.app.logger) {
            window.app.logger.log(this.to.name, `Read from Pipe`, `"${msg.data}" ← ${this.from.name} [${this.buffer.length}/${this.bufferSize}]`, 'receive');
        }

        return { success: true, data: msg.data };
    }

    getUtilization() {
        return this.buffer.length / this.bufferSize;
    }

    isFull() {
        return this.buffer.length >= this.bufferSize;
    }

    isEmpty() {
        return this.buffer.length === 0;
    }

    clear() {
        this.buffer = [];
        this.totalWritten = 0;
        this.totalRead = 0;
        this.isActive = false;
    }
}

class PipeManager {
    constructor() {
        this.pipes = new Map();
        this.nextId = 1;
    }

    createPipe(fromProcess, toProcess, bufferSize = 5) {
        const id = this.nextId++;
        const pipe = new Pipe(id, fromProcess, toProcess, bufferSize);
        this.pipes.set(id, pipe);
        return pipe;
    }

    getPipe(id) {
        return this.pipes.get(id);
    }

    getAllPipes() {
        return Array.from(this.pipes.values());
    }

    clear() {
        this.pipes.clear();
        this.nextId = 1;
    }
}

window.Pipe = Pipe;
window.PipeManager = PipeManager;
