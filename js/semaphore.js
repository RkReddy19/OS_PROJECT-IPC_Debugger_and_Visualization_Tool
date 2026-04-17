/* =====================================================
   Semaphore Module — Synchronization primitive
   ===================================================== */

class Semaphore {
  constructor(id, initialValue = 1) {
    this.id = id;
    this.value = initialValue;
    this.maxValue = initialValue;
    this.waitQueue = []; // Processes waiting for this semaphore
    this.heldBy = null; // Process currently holding it (for binary semaphore)
    this.type = 'semaphore';
  }

  wait(process) {
    if (this.value > 0) {
      this.value--;
      this.heldBy = process.id;

      if (window.app && window.app.logger) {
        window.app.logger.log(
          process.name,
          `Acquired Semaphore`,
          `S${this.id} (value: ${this.value})`,
          'system'
        );
      }

      return { success: true, acquired: true };
    } else {
      // Process must wait
      this.waitQueue.push(process.id);
      process.waitFor(`sem_${this.id}`);

      if (window.app && window.app.logger) {
        window.app.logger.log(
          process.name,
          `Waiting on Semaphore`,
          `S${this.id} — queue: [${this.waitQueue
            .map((id) => {
              const p = window.app.processManager.getProcess(id);
              return p ? p.name : id;
            })
            .join(', ')}]`,
          'wait'
        );
      }

      return { success: true, acquired: false };
    }
  }

  signal(process) {
    this.value++;

    if (window.app && window.app.logger) {
      window.app.logger.log(
        process.name,
        `Released Semaphore`,
        `S${this.id} (value: ${this.value})`,
        'system'
      );
    }

    // Wake up waiting process
    if (this.waitQueue.length > 0) {
      const nextProcessId = this.waitQueue.shift();
      this.value--;
      this.heldBy = nextProcessId;

      const nextProcess = window.app ? window.app.processManager.getProcess(nextProcessId) : null;
      if (nextProcess) {
        nextProcess.unblock();
        if (window.app && window.app.logger) {
          window.app.logger.log(
            nextProcess.name,
            `Acquired Semaphore (woken)`,
            `S${this.id}`,
            'system'
          );
        }
      }
    } else {
      this.heldBy = null;
    }

    return { success: true };
  }

  isLocked() {
    return this.value === 0;
  }

  clear() {
    this.value = this.maxValue;
    this.waitQueue = [];
    this.heldBy = null;
  }
}

class SemaphoreManager {
  constructor() {
    this.semaphores = new Map();
    this.nextId = 1;
  }

  createSemaphore(initialValue = 1) {
    const id = this.nextId++;
    const sem = new Semaphore(id, initialValue);
    this.semaphores.set(id, sem);
    return sem;
  }

  getSemaphore(id) {
    return this.semaphores.get(id);
  }

  getAllSemaphores() {
    return Array.from(this.semaphores.values());
  }

  clear() {
    this.semaphores.clear();
    this.nextId = 1;
  }
}

window.Semaphore = Semaphore;
window.SemaphoreManager = SemaphoreManager;
