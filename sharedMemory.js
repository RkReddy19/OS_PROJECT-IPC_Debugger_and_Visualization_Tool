/* =====================================================
   Shared Memory IPC Module — Concurrent memory access
   ===================================================== */

class SharedMemory {
    constructor(id, size = 256) {
        this.id = id;
        this.size = size;
        this.data = {};
        this.type = 'shm';
        this.accessLog = [];
        this.activeReaders = new Set();
        this.activeWriter = null;
        this.raceConditions = [];
        this.totalReads = 0;
        this.totalWrites = 0;
        this.attachedProcesses = new Set();
    }

    attach(process) {
        this.attachedProcesses.add(process.id);
        if (window.app && window.app.logger) {
            window.app.logger.log(process.name, 'Attached to SharedMem', `SHM ${this.id}`, 'system');
        }
    }

    detach(process) {
        this.attachedProcesses.delete(process.id);
        this.activeReaders.delete(process.id);
        if (this.activeWriter === process.id) this.activeWriter = null;
    }

    write(process, key, value) {
        const access = {
            type: 'write',
            processId: process.id,
            processName: process.name,
            key,
            value,
            tick: window.app ? window.app.tick : 0
        };

        // Check for race condition: another process is writing simultaneously
        if (this.activeWriter !== null && this.activeWriter !== process.id) {
            const race = {
                tick: access.tick,
                process1: this.activeWriter,
                process2: process.id,
                key,
                description: `Concurrent write to SharedMem key "${key}"`
            };
            this.raceConditions.push(race);

            if (window.app && window.app.logger) {
                window.app.logger.log(process.name, '⚠ RACE CONDITION', `Concurrent write on "${key}" in SHM ${this.id}`, 'deadlock');
            }
        }

        // Check for read-write race
        if (this.activeReaders.size > 0) {
            const readers = [...this.activeReaders].filter(r => r !== process.id);
            if (readers.length > 0) {
                const race = {
                    tick: access.tick,
                    writer: process.id,
                    readers: readers,
                    key,
                    description: `Write while read in progress on "${key}"`
                };
                this.raceConditions.push(race);

                if (window.app && window.app.logger) {
                    window.app.logger.log(process.name, '⚠ RACE CONDITION', `Write during active read on "${key}"`, 'deadlock');
                }
            }
        }

        this.activeWriter = process.id;
        this.data[key] = value;
        this.accessLog.push(access);
        this.totalWrites++;

        if (window.app && window.app.logger) {
            window.app.logger.log(process.name, `Wrote to SharedMem`, `"${key}" = ${value}`, 'send');
        }

        // Writer finishes after a simulated delay
        setTimeout(() => {
            if (this.activeWriter === process.id) {
                this.activeWriter = null;
            }
        }, 0);

        return { success: true };
    }

    read(process, key) {
        this.activeReaders.add(process.id);
        const value = this.data[key];
        this.totalReads++;

        const access = {
            type: 'read',
            processId: process.id,
            processName: process.name,
            key,
            value,
            tick: window.app ? window.app.tick : 0
        };
        this.accessLog.push(access);

        if (window.app && window.app.logger) {
            window.app.logger.log(process.name, `Read from SharedMem`, `"${key}" = ${value}`, 'receive');
        }

        // Reader finishes
        setTimeout(() => {
            this.activeReaders.delete(process.id);
        }, 0);

        return { success: true, value };
    }

    clearWriteLock() {
        this.activeWriter = null;
        this.activeReaders.clear();
    }

    clear() {
        this.data = {};
        this.accessLog = [];
        this.activeReaders.clear();
        this.activeWriter = null;
        this.raceConditions = [];
        this.totalReads = 0;
        this.totalWrites = 0;
        this.attachedProcesses.clear();
    }
}

class SharedMemoryManager {
    constructor() {
        this.segments = new Map();
        this.nextId = 1;
    }

    createSegment(size = 256) {
        const id = this.nextId++;
        const shm = new SharedMemory(id, size);
        this.segments.set(id, shm);
        return shm;
    }

    getSegment(id) {
        return this.segments.get(id);
    }

    getAllSegments() {
        return Array.from(this.segments.values());
    }

    getAllRaceConditions() {
        const races = [];
        this.segments.forEach(shm => {
            races.push(...shm.raceConditions);
        });
        return races;
    }

    clear() {
        this.segments.clear();
        this.nextId = 1;
    }
}

window.SharedMemory = SharedMemory;
window.SharedMemoryManager = SharedMemoryManager;
