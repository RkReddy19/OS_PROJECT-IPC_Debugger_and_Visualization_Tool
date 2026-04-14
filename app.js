/* =====================================================
   App Controller — Main orchestrator for IPC Debugger
   ===================================================== */

class App {
    constructor() {
        this.tick = 0;
        this.isRunning = false;
        this.speed = 1000;
        this.intervalId = null;

        // Modules
        this.logger = new Logger();
        this.processManager = new ProcessManager();
        this.pipeManager = new PipeManager();
        this.queueManager = new MessageQueueManager();
        this.shmManager = new SharedMemoryManager();
        this.semManager = new SemaphoreManager();
        this.debugger = new IPCDebugger();
        this.timeline = new Timeline();
        this.visualizer = null;

        // Scenario state
        this.currentScenario = null;
        this.scenarioSteps = [];
        this.stepIndex = 0;

        // Connections for visualization
        this.connections = [];

        // Metrics
        this.metrics = {
            messagesSent: 0,
            messagesReceived: 0,
            deadlocks: 0,
            bottlenecks: 0
        };

        // DOM Cache for performance
        this.domCache = new Map();
    }

    getDOMElement(id) {
        if (!this.domCache.has(id)) {
            this.domCache.set(id, document.getElementById(id));
        }
        return this.domCache.get(id);
    }

    init() {
        window.app = this;
        this.visualizer = new Visualizer('viz-canvas');
        this.bindEvents();
        this.updateUI();
        this.logger.log(null, 'IPC Debugger initialized', 'Ready for simulation', 'system');
        this.renderVisualization();
    }

    bindEvents() {
        const events = [
            ['btn-play', () => this.play()],
            ['btn-pause', () => this.pause()],
            ['btn-step', () => this.step()],
            ['btn-reset', () => this.reset()],
            ['btn-export', () => this.logger.exportReport()],
            ['create-custom-btn', () => this.createCustomProcesses()]
        ];

        events.forEach(([id, handler]) => {
            const el = this.getDOMElement(id);
            el?.addEventListener('click', handler);
        });

        const speedSlider = this.getDOMElement('speed-slider');
        speedSlider?.addEventListener('input', (e) => {
            const val = parseInt(e.target.value);
            this.speed = 2000 - (val * 180);
            const speedValue = this.getDOMElement('speed-value');
            if (speedValue) speedValue.textContent = `${val}x`;
            if (this.isRunning) {
                this.pause();
                this.play();
            }
        });

        const scenarioSelect = this.getDOMElement('scenario-select');
        scenarioSelect?.addEventListener('change', (e) => {
            this.loadScenario(e.target.value);
        });

        const customProcessInput = this.getDOMElement('custom-process-input');
        customProcessInput?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.createCustomProcesses();
            }
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Only if not typing in an input
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') {
                return;
            }
            
            switch(e.code) {
                case 'Space':
                    e.preventDefault();
                    if (this.isRunning) this.pause();
                    else this.play();
                    break;
                case 'ArrowRight':
                    e.preventDefault();
                    this.step();
                    break;
                case 'KeyR':
                    if (e.ctrlKey || e.metaKey) return; // Allow browser refresh
                    e.preventDefault();
                    this.reset();
                    break;
            }
        });

        // Event delegation for add process buttons
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('btn-add-process')) {
                e.stopPropagation();
                this.showAddProcessDialog();
            }
        });

        // Tab switching with event delegation
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('panel-tab')) {
                const panel = e.target.closest('.card');
                const tabs = panel.querySelectorAll('.panel-tab');
                const contents = panel.querySelectorAll('.tab-content');
                
                tabs.forEach(t => t.classList.remove('active'));
                contents.forEach(c => c.classList.remove('active'));
                
                e.target.classList.add('active');
                const targetId = e.target.dataset.tab;
                this.getDOMElement(targetId)?.classList.add('active');
            }
        });
    }

    play() {
        if (this.isRunning) return;
        if (!this.currentScenario) {
            this.logger.log(null, 'No scenario loaded', 'Please select a scenario from the Control Panel first', 'system');
            this.showToast('Please select a scenario to begin', 'warning');
            return;
        }
        this.isRunning = true;
        this.updateControlState();
        this.logger.log(null, 'Simulation STARTED', `Speed: ${this.speed}ms/tick`, 'system');

        this.intervalId = setInterval(() => {
            this.step();
            if (this.stepIndex >= this.scenarioSteps.length && this.isRunning) {
                this.tick++;
                this.timeline.recordTick(this.processManager, this.tick);
                this.debugger.runAllChecks(this.processManager, this.pipeManager, this.queueManager, this.shmManager);
                this.updateUI();
                this.renderVisualization();
            }
        }, this.speed);
    }

    pause() {
        this.isRunning = false;
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
        this.updateControlState();
        this.logger.log(null, 'Simulation PAUSED', `Tick: ${this.tick}`, 'system');
    }

    step() {
        if (this.stepIndex < this.scenarioSteps.length) {
            this.tick++;
            const stepFn = this.scenarioSteps[this.stepIndex];
            stepFn(this);
            this.stepIndex++;

            this.timeline.recordTick(this.processManager, this.tick);
            this.debugger.runAllChecks(this.processManager, this.pipeManager, this.queueManager, this.shmManager);
            this.updateUI();
            this.renderVisualization();
        } else if (this.stepIndex >= this.scenarioSteps.length && !this.isRunning) {
            this.tick++;
            this.timeline.recordTick(this.processManager, this.tick);
            this.debugger.runAllChecks(this.processManager, this.pipeManager, this.queueManager, this.shmManager);
            this.updateUI();
            this.renderVisualization();
            this.logger.log(null, 'Scenario complete', 'All steps executed', 'system');
        }
    }

    reset() {
        this.pause();
        this.tick = 0;
        this.stepIndex = 0;
        this.connections = [];
        this.metrics = { messagesSent: 0, messagesReceived: 0, deadlocks: 0, bottlenecks: 0 };

        this.processManager.clear();
        this.pipeManager.clear();
        this.queueManager.clear();
        this.shmManager.clear();
        this.semManager.clear();
        this.debugger.clear();
        this.timeline.clear();
        this.logger.clear();
        this.visualizer.clear();

        this.currentScenario = null;
        this.scenarioSteps = [];

        const scenarioSelect = this.getDOMElement('scenario-select');
        if (scenarioSelect) scenarioSelect.value = '';
        this.updateUI();
        this.renderVisualization();
        this.logger.log(null, 'Simulation RESET', '', 'system');
    }

    // ----- Scenario Loading -----

    loadScenario(scenarioName) {
        if (!scenarioName) return;
        this.reset();
        this.currentScenario = scenarioName;

        // Show/hide custom process input
        const customSection = this.getDOMElement('custom-process-section');
        if (customSection) {
            customSection.style.display = scenarioName === 'custom' ? 'block' : 'none';
        }

        switch (scenarioName) {
            case 'normal-pipe':
                this.setupNormalPipeScenario();
                break;
            case 'normal-queue':
                this.setupNormalQueueScenario();
                break;
            case 'deadlock':
                this.setupDeadlockScenario();
                break;
            case 'race-condition':
                this.setupRaceConditionScenario();
                break;
            case 'bottleneck':
                this.setupBottleneckScenario();
                break;
            case 'complex':
                this.setupComplexScenario();
                break;
            case 'custom':
                // Custom processes will be created by user input
                this.logger.log(null, 'Custom mode active', 'Enter process names to begin', 'system');
                return;
        }

        this.processManager.renderProcessList();
        this.renderConnectionList();
        this.updateUI();
        this.renderVisualization();
        this.logger.log(null, `Scenario loaded: ${scenarioName}`, `${this.scenarioSteps.length} steps`, 'system');
    }

    // ----- Custom Process Creation -----

    createCustomProcesses() {
        const input = this.getDOMElement('custom-process-input');
        if (!input || !input.value.trim()) {
            this.logger.log(null, 'Input error', 'Please enter process names', 'system');
            return;
        }

        // Parse input: "P1,P2,P3" or "P1, P2, P3"
        const processNames = input.value
            .split(',')
            .map(name => name.trim().toUpperCase())
            .filter(name => name.length > 0);

        if (processNames.length === 0) {
            this.logger.log(null, 'Input error', 'No valid process names found', 'system');
            return;
        }

        // Check for duplicates
        const uniqueNames = new Set(processNames);
        if (uniqueNames.size !== processNames.length) {
            this.logger.log(null, 'Input error', 'Duplicate process names found', 'system');
            return;
        }

        // Clear existing scenario
        this.pause();
        this.tick = 0;
        this.stepIndex = 0;
        this.connections = [];
        this.metrics = { messagesSent: 0, messagesReceived: 0, deadlocks: 0, bottlenecks: 0 };
        this.processManager.clear();
        this.pipeManager.clear();
        this.queueManager.clear();
        this.shmManager.clear();
        this.semManager.clear();
        this.debugger.clear();
        this.timeline.clear();
        this.logger.clear();
        this.visualizer.clear();

        // Create custom processes
        const processes = [];
        processNames.forEach((name, index) => {
            const p = this.processManager.createProcess(name);
            p.setState(index === 0 ? 'running' : 'ready');
            processes.push(p);
        });

        // Create a simple scenario: processes communicate in sequence
        this.scenarioSteps = [];
        
        // Step 1: Initialize all processes
        this.scenarioSteps.push((app) => {
            processes.forEach((p, i) => {
                p.setState('running');
                app.timeline.recordEvent(p.id, 'send');
            });
            app.logger.log(null, 'Custom processes initialized', `Total: ${processes.length}`, 'system');
        });

        // Step 2: Create connections between consecutive processes (pipe communication)
        for (let i = 0; i < processes.length - 1; i++) {
            const from = processes[i];
            const to = processes[i + 1];
            const pipe = this.pipeManager.createPipe(from, to, 3);
            this.connections.push({ fromId: from.id, toId: to.id, type: 'pipe', ref: pipe });
        }

        // Step 3: Add communication steps
        for (let i = 0; i < processes.length - 1; i++) {
            this.scenarioSteps.push((app) => {
                const from = processes[i];
                const to = processes[i + 1];
                from.setState('running');
                
                const pipe = app.pipeManager.pipes.find(p => p.sender.id === from.id && p.receiver.id === to.id);
                if (pipe) {
                    pipe.write(`Message_${i}`);
                    app.metrics.messagesSent++;
                    app.timeline.recordEvent(from.id, 'send');
                    app.visualizer.addDataParticle(from, to, '#6366f1');
                }
            });

            this.scenarioSteps.push((app) => {
                const to = processes[i + 1];
                to.setState('running');
                
                const pipe = app.pipeManager.pipes.find(p => p.receiver.id === to.id);
                if (pipe) {
                    const result = pipe.read();
                    if (result.success) {
                        app.metrics.messagesReceived++;
                        app.timeline.recordEvent(to.id, 'receive');
                    }
                }
            });
        }

        // Final step: Terminate all
        this.scenarioSteps.push((app) => {
            processes.forEach(p => p.setState('terminated'));
            app.logger.log(null, 'Custom scenario complete', 'All processes terminated', 'system');
        });

        this.currentScenario = 'custom';
        this.processManager.renderProcessList();
        this.renderConnectionList();
        this.updateUI();
        this.renderVisualization();
        this.logger.log(null, 'Custom scenario created', `Processes: ${processNames.join(', ')}`, 'system');
    }

    // ----- Add Process Dynamically -----

    showAddProcessDialog() {
        const processNameInput = prompt('Enter new process name (e.g., P6):');
        
        if (processNameInput === null) {
            return; // User cancelled
        }

        const name = processNameInput.trim().toUpperCase();
        
        if (!name) {
            this.logger.log(null, 'Input error', 'Process name cannot be empty', 'system');
            return;
        }

        // Check if process name already exists
        if (this.processManager.getProcessByName(name)) {
            this.logger.log(null, 'Duplicate error', `Process ${name} already exists`, 'system');
            return;
        }

        this.addNewProcess(name);
    }

    addNewProcess(name) {
        // Create new process
        const newProcess = this.processManager.createProcess(name);
        newProcess.setState('ready');

        // If we're in the middle of running, pause to add the process safely
        const wasRunning = this.isRunning;
        if (wasRunning) {
            this.pause();
        }

        // Create connection from last process to new process (pipe)
        const allProcesses = this.processManager.getAllProcesses();
        if (allProcesses.length > 1) {
            const lastProcess = allProcesses[allProcesses.length - 2]; // Get the one before the newly added
            const pipe = this.pipeManager.createPipe(lastProcess, newProcess, 3);
            this.connections.push({ 
                fromId: lastProcess.id, 
                toId: newProcess.id, 
                type: 'pipe', 
                ref: pipe 
            });
        }

        // Add communication steps for the new process
        const lastProcess = allProcesses[allProcesses.length - 2];
        
        this.scenarioSteps.push((app) => {
            lastProcess.setState('running');
            const pipe = app.pipeManager.pipes.find(p => p.sender.id === lastProcess.id && p.receiver.id === newProcess.id);
            if (pipe) {
                pipe.write(`Message_${newProcess.name}`);
                app.metrics.messagesSent++;
                app.timeline.recordEvent(lastProcess.id, 'send');
                app.visualizer.addDataParticle(lastProcess, newProcess, '#6366f1');
            }
        });

        this.scenarioSteps.push((app) => {
            newProcess.setState('running');
            const pipe = app.pipeManager.pipes.find(p => p.receiver.id === newProcess.id);
            if (pipe) {
                const result = pipe.read();
                if (result.success) {
                    app.metrics.messagesReceived++;
                    app.timeline.recordEvent(newProcess.id, 'receive');
                }
            }
        });

        // Update UI
        this.processManager.renderProcessList();
        this.renderConnectionList();
        this.updateUI();
        this.renderVisualization();

        this.logger.log(null, 'Process added', `New process ${name} created and connected`, 'system');

        // Resume simulation if it was running
        if (wasRunning) {
            this.play();
        }
    }

    // ----- Scenario: Normal Pipe Communication -----
    setupNormalPipeScenario() {
        const p1 = this.processManager.createProcess('P1');
        const p2 = this.processManager.createProcess('P2');
        p1.setState('running');
        p2.setState('ready');

        const pipe = this.pipeManager.createPipe(p1, p2, 5);
        this.connections.push({ fromId: p1.id, toId: p2.id, type: 'pipe', ref: pipe });

        const messages = ['Hello', 'World', 'IPC', 'Works', 'Great'];

        messages.forEach((msg, i) => {
            // Send step
            this.scenarioSteps.push((app) => {
                p1.setState('running');
                pipe.write(msg);
                app.metrics.messagesSent++;
                app.timeline.recordEvent(p1.id, 'send');
                app.visualizer.addDataParticle(p1, p2, '#6366f1');
            });
            // Receive step
            this.scenarioSteps.push((app) => {
                p2.setState('running');
                const result = pipe.read();
                if (result.success) {
                    app.metrics.messagesReceived++;
                    app.timeline.recordEvent(p2.id, 'receive');
                }
                p1.setState('waiting');
            });
        });

        // Final step
        this.scenarioSteps.push((app) => {
            p1.setState('terminated');
            p2.setState('terminated');
            app.logger.log(null, 'Pipe communication complete', 'All messages delivered successfully', 'system');
        });
    }

    // ----- Scenario: Normal Queue Communication -----
    setupNormalQueueScenario() {
        const p1 = this.processManager.createProcess('P1');
        const p2 = this.processManager.createProcess('P2');
        const p3 = this.processManager.createProcess('P3');
        p1.setState('running');
        p2.setState('running');
        p3.setState('ready');

        const queue = this.queueManager.createQueue(8);
        this.connections.push({ fromId: p1.id, toId: p3.id, type: 'queue', ref: queue });
        this.connections.push({ fromId: p2.id, toId: p3.id, type: 'queue', ref: queue });

        const messages1 = ['Task-A', 'Task-B', 'Task-C'];
        const messages2 = ['Job-X', 'Job-Y'];

        // P1 sends
        messages1.forEach(msg => {
            this.scenarioSteps.push((app) => {
                p1.setState('running');
                queue.send(p1, msg, 1);
                app.metrics.messagesSent++;
                app.timeline.recordEvent(p1.id, 'send');
                app.visualizer.addDataParticle(p1, p3, '#22d3ee');
            });
        });

        // P2 sends
        messages2.forEach(msg => {
            this.scenarioSteps.push((app) => {
                p2.setState('running');
                queue.send(p2, msg, 0);
                app.metrics.messagesSent++;
                app.timeline.recordEvent(p2.id, 'send');
                app.visualizer.addDataParticle(p2, p3, '#22d3ee');
            });
        });

        // P3 receives all
        for (let i = 0; i < 5; i++) {
            this.scenarioSteps.push((app) => {
                p3.setState('running');
                const result = queue.receive(p3);
                if (result.success) {
                    app.metrics.messagesReceived++;
                    app.timeline.recordEvent(p3.id, 'receive');
                }
            });
        }

        this.scenarioSteps.push((app) => {
            p1.setState('terminated');
            p2.setState('terminated');
            p3.setState('terminated');
            app.logger.log(null, 'Queue communication complete', 'All messages processed', 'system');
        });
    }

    // ----- Scenario: Deadlock -----
    setupDeadlockScenario() {
        const p1 = this.processManager.createProcess('P1');
        const p2 = this.processManager.createProcess('P2');
        p1.setState('running');
        p2.setState('running');

        // No physical IPC connection here — just resource contention
        // Visual connection to show the relationship
        this.connections.push({ fromId: p1.id, toId: p2.id, type: 'pipe', ref: { getUtilization: () => 0 } });

        this.scenarioSteps.push((app) => {
            app.logger.log('P1', 'Acquired Resource A', 'Holding R_A', 'system');
            p1.holdResource('R_A');
            p1.setState('running');
        });

        this.scenarioSteps.push((app) => {
            app.logger.log('P2', 'Acquired Resource B', 'Holding R_B', 'system');
            p2.holdResource('R_B');
            p2.setState('running');
        });

        this.scenarioSteps.push((app) => {
            app.logger.log('P1', 'Requesting Resource B', 'Waiting...', 'wait');
            p1.waitFor('R_B');
        });

        this.scenarioSteps.push((app) => {
            app.logger.log('P2', 'Requesting Resource A', 'Waiting...', 'wait');
            p2.waitFor('R_A');
            // Deadlock will be detected by the debugger on next check
        });

        // Extra ticks to observe the deadlock
        for (let i = 0; i < 5; i++) {
            this.scenarioSteps.push((app) => {
                // Just ticking — deadlock persists
            });
        }
    }

    // ----- Scenario: Race Condition -----
    setupRaceConditionScenario() {
        const p1 = this.processManager.createProcess('P1');
        const p2 = this.processManager.createProcess('P2');
        const p3 = this.processManager.createProcess('P3');
        p1.setState('running');
        p2.setState('running');
        p3.setState('ready');

        const shm = this.shmManager.createSegment(256);
        shm.attach(p1);
        shm.attach(p2);
        shm.attach(p3);

        this.connections.push({ fromId: p1.id, toId: p2.id, type: 'shm', ref: shm });
        this.connections.push({ fromId: p2.id, toId: p3.id, type: 'shm', ref: shm });

        // Initialize shared counter
        this.scenarioSteps.push((app) => {
            shm.write(p1, 'counter', 0);
            app.logger.log('SYS', 'Shared counter initialized', 'counter = 0', 'system');
        });

        // P1 and P2 write to counter simultaneously (race condition!)
        this.scenarioSteps.push((app) => {
            p1.setState('running');
            const val = shm.read(p1, 'counter');
            shm.activeWriter = p2.id; // Simulate P2 also writing at the same time
            shm.write(p1, 'counter', (val.value || 0) + 1);
            app.timeline.recordEvent(p1.id, 'send');
        });

        this.scenarioSteps.push((app) => {
            p2.setState('running');
            const val = shm.read(p2, 'counter');
            shm.activeWriter = p1.id; // Simulate concurrent write
            shm.write(p2, 'counter', (val.value || 0) + 1);
            app.timeline.recordEvent(p2.id, 'send');
        });

        // Show the result — counter may not be 2 due to race
        this.scenarioSteps.push((app) => {
            p3.setState('running');
            const val = shm.read(p3, 'counter');
            app.logger.log('P3', `Read counter = ${val.value}`, 'Expected: 2, race condition may have caused data loss', 'receive');
            app.timeline.recordEvent(p3.id, 'receive');
        });

        // Now demonstrate with semaphore (safe version)
        this.scenarioSteps.push((app) => {
            app.logger.log('SYS', '── Now with Semaphore ──', 'Protected access demo', 'system');
            shm.clearWriteLock();
            shm.write(p1, 'safe_counter', 0);
        });

        const sem = this.semManager.createSemaphore(1);

        this.scenarioSteps.push((app) => {
            sem.wait(p1);
            shm.clearWriteLock();
            const val = shm.read(p1, 'safe_counter');
            shm.write(p1, 'safe_counter', (val.value || 0) + 1);
            sem.signal(p1);
            app.timeline.recordEvent(p1.id, 'send');
        });

        this.scenarioSteps.push((app) => {
            sem.wait(p2);
            shm.clearWriteLock();
            const val = shm.read(p2, 'safe_counter');
            shm.write(p2, 'safe_counter', (val.value || 0) + 1);
            sem.signal(p2);
            app.timeline.recordEvent(p2.id, 'send');
        });

        this.scenarioSteps.push((app) => {
            const val = shm.read(p3, 'safe_counter');
            app.logger.log('P3', `Safe counter = ${val.value}`, 'Correctly = 2, semaphore prevented race', 'receive');
        });

        this.scenarioSteps.push((app) => {
            p1.setState('terminated');
            p2.setState('terminated');
            p3.setState('terminated');
        });
    }

    // ----- Scenario: Bottleneck -----
    setupBottleneckScenario() {
        const p1 = this.processManager.createProcess('P1');
        const p2 = this.processManager.createProcess('P2');
        p1.setState('running');
        p2.setState('ready');

        const queue = this.queueManager.createQueue(4); // Small capacity
        this.connections.push({ fromId: p1.id, toId: p2.id, type: 'queue', ref: queue });

        const data = ['Msg1', 'Msg2', 'Msg3', 'Msg4', 'Msg5', 'Msg6', 'Msg7', 'Msg8'];

        // P1 floods the queue
        data.forEach(msg => {
            this.scenarioSteps.push((app) => {
                p1.setState('running');
                const result = queue.send(p1, msg);
                if (result.success) {
                    app.metrics.messagesSent++;
                    app.timeline.recordEvent(p1.id, 'send');
                    app.visualizer.addDataParticle(p1, p2, '#22d3ee');
                } else {
                    p1.setState('blocked');
                    app.timeline.recordEvent(p1.id, 'blocked');
                }
            });
        });

        // P2 slowly consumes
        for (let i = 0; i < 4; i++) {
            this.scenarioSteps.push((app) => {
                p2.setState('running');
                const result = queue.receive(p2);
                if (result.success) {
                    app.metrics.messagesReceived++;
                    app.timeline.recordEvent(p2.id, 'receive');
                }
                p1.setState('running');
            });
        }

        this.scenarioSteps.push((app) => {
            p1.setState('terminated');
            p2.setState('terminated');
        });
    }

    // ----- Scenario: Complex Multi-IPC -----
    setupComplexScenario() {
        const p1 = this.processManager.createProcess('P1');
        const p2 = this.processManager.createProcess('P2');
        const p3 = this.processManager.createProcess('P3');
        const p4 = this.processManager.createProcess('P4');
        p1.setState('running');
        p2.setState('running');
        p3.setState('running');
        p4.setState('ready');

        const pipe12 = this.pipeManager.createPipe(p1, p2, 3);
        const queue23 = this.queueManager.createQueue(4);
        const shm34 = this.shmManager.createSegment();
        shm34.attach(p3);
        shm34.attach(p4);

        this.connections.push({ fromId: p1.id, toId: p2.id, type: 'pipe', ref: pipe12 });
        this.connections.push({ fromId: p2.id, toId: p3.id, type: 'queue', ref: queue23 });
        this.connections.push({ fromId: p3.id, toId: p4.id, type: 'shm', ref: shm34 });

        // P1 → Pipe → P2
        this.scenarioSteps.push((app) => {
            pipe12.write('DataA');
            app.metrics.messagesSent++;
            app.timeline.recordEvent(p1.id, 'send');
            app.visualizer.addDataParticle(p1, p2, '#6366f1');
        });

        this.scenarioSteps.push((app) => {
            const result = pipe12.read();
            if (result.success) app.metrics.messagesReceived++;
            p2.setState('running');
            app.timeline.recordEvent(p2.id, 'receive');
        });

        // P2 → Queue → P3
        this.scenarioSteps.push((app) => {
            queue23.send(p2, 'Processed-DataA');
            app.metrics.messagesSent++;
            app.timeline.recordEvent(p2.id, 'send');
            app.visualizer.addDataParticle(p2, p3, '#22d3ee');
        });

        this.scenarioSteps.push((app) => {
            const result = queue23.receive(p3);
            if (result.success) app.metrics.messagesReceived++;
            app.timeline.recordEvent(p3.id, 'receive');
        });

        // P3 → SharedMem → P4
        this.scenarioSteps.push((app) => {
            shm34.clearWriteLock();
            shm34.write(p3, 'result', 'FinalOutput');
            app.timeline.recordEvent(p3.id, 'send');
            app.visualizer.addDataParticle(p3, p4, '#a78bfa');
        });

        this.scenarioSteps.push((app) => {
            p4.setState('running');
            shm34.read(p4, 'result');
            app.timeline.recordEvent(p4.id, 'receive');
        });

        // More pipe data
        this.scenarioSteps.push((app) => {
            pipe12.write('DataB');
            pipe12.write('DataC');
            app.metrics.messagesSent += 2;
            app.timeline.recordEvent(p1.id, 'send');
            app.visualizer.addDataParticle(p1, p2, '#6366f1');
        });

        this.scenarioSteps.push((app) => {
            pipe12.read();
            pipe12.read();
            app.metrics.messagesReceived += 2;
            app.timeline.recordEvent(p2.id, 'receive');
        });

        // Queue flood for bottleneck
        this.scenarioSteps.push((app) => {
            queue23.send(p2, 'Bulk1');
            queue23.send(p2, 'Bulk2');
            queue23.send(p2, 'Bulk3');
            queue23.send(p2, 'Bulk4');
            app.metrics.messagesSent += 4;
            app.timeline.recordEvent(p2.id, 'send');
        });

        this.scenarioSteps.push((app) => {
            queue23.receive(p3);
            queue23.receive(p3);
            app.metrics.messagesReceived += 2;
            app.timeline.recordEvent(p3.id, 'receive');
        });

        // Process results
        this.scenarioSteps.push((app) => {
            shm34.clearWriteLock();
            shm34.write(p3, 'status', 'COMPLETE');
            app.timeline.recordEvent(p3.id, 'send');
        });

        this.scenarioSteps.push((app) => {
            p4.setState('running');
            shm34.read(p4, 'status');
            app.timeline.recordEvent(p4.id, 'receive');
            app.logger.log('SYS', 'Pipeline complete', 'P1→P2→P3→P4 data flow finished', 'system');
        });

        this.scenarioSteps.push((app) => {
            p1.setState('terminated');
            p2.setState('terminated');
            p3.setState('terminated');
            p4.setState('terminated');
        });
    }

    // ----- UI Updates -----

    updateUI() {
        const tickEl = this.getDOMElement('tick-counter');
        if (tickEl) tickEl.textContent = `Tick: ${this.tick}`;

        const statusBadge = this.getDOMElement('sim-status');
        if (statusBadge) {
            if (this.isRunning) {
                statusBadge.className = 'badge running';
                statusBadge.textContent = '● Running';
            } else if (this.tick > 0) {
                statusBadge.className = 'badge paused';
                statusBadge.textContent = '● Paused';
            } else {
                statusBadge.className = 'badge stopped';
                statusBadge.textContent = '● Stopped';
            }
        }

        this.updateMetric('metric-sent', this.metrics.messagesSent, 'indigo');
        this.updateMetric('metric-received', this.metrics.messagesReceived, 'cyan');
        this.updateMetric('metric-deadlocks', this.debugger.deadlockHistory.length, 'rose');
        this.updateMetric('metric-alerts', this.debugger.alerts.length, 'amber');

        this.processManager.renderProcessList();
        this.timeline.render(this.processManager, this.tick);
        
        // Update empty state visibility
        this.updateEmptyStates();
    }

    updateEmptyStates() {
        // Hide/show visualization empty state
        const vizEmptyState = this.getDOMElement('viz-empty-state');
        const vizCanvas = this.getDOMElement('viz-canvas');
        const hasProcesses = this.processManager.getAllProcesses().length > 0;
        
        if (vizEmptyState && vizCanvas) {
            vizEmptyState.style.display = hasProcesses ? 'none' : 'flex';
            vizCanvas.style.display = hasProcesses ? 'block' : 'none';
        }
        
        // Update process list empty state
        const processList = this.getDOMElement('process-list');
        if (processList && hasProcesses) {
            const emptyState = processList.querySelector('.empty-state');
            if (emptyState) emptyState.style.display = 'none';
        }
        
        // Update event log empty state
        const eventLog = this.getDOMElement('event-log');
        if (eventLog && this.logger.logs.length > 0) {
            const emptyState = eventLog.querySelector('.empty-state');
            if (emptyState) emptyState.style.display = 'none';
        }
    }

    updateMetric(id, value, colorClass) {
        const el = this.getDOMElement(id);
        if (el) {
            el.textContent = value;
            el.className = `metric-value ${colorClass}`;
        }
    }

    updateControlState() {
        const playBtn = this.getDOMElement('btn-play');
        const pauseBtn = this.getDOMElement('btn-pause');
        if (playBtn) playBtn.style.opacity = this.isRunning ? '0.5' : '1';
        if (pauseBtn) pauseBtn.style.opacity = this.isRunning ? '1' : '0.5';
    }

    showToast(message, type = 'info') {
        // Create a simple toast notification
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: ${type === 'warning' ? 'rgba(251, 191, 36, 0.15)' : 'rgba(99, 102, 241, 0.15)'};
            border: 1px solid ${type === 'warning' ? '#fbbf24' : '#6366f1'};
            border-radius: 8px;
            padding: 12px 16px;
            font-size: 14px;
            color: ${type === 'warning' ? '#fcd34d' : '#a5b4fc'};
            z-index: 10000;
            animation: slideUp 0.3s ease;
            max-width: 300px;
        `;
        toast.textContent = message;
        document.body.appendChild(toast);
        
        // Auto-remove after 4 seconds
        setTimeout(() => {
            toast.style.animation = 'none';
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(20px)';
            setTimeout(() => toast.remove(), 200);
        }, 4000);
    }

    renderVisualization() {
        const processes = this.processManager.getAllProcesses();

        // Build connection objects with utilization info
        const vizConnections = this.connections.map(conn => ({
            fromId: conn.fromId,
            toId: conn.toId,
            type: conn.type,
            isActive: conn.ref.isActive || (conn.ref.queue && conn.ref.queue.length > 0) ||
                (conn.ref.buffer && conn.ref.buffer.length > 0),
            utilization: conn.ref.getUtilization ? conn.ref.getUtilization() : 0
        }));

        // Check for deadlock cycles
        const cycles = this.debugger.findCycles(this.debugger.buildWaitForGraph(this.processManager));

        this.visualizer.render(processes, vizConnections, cycles);
    }

    renderConnectionList() {
        const container = this.getDOMElement('connection-list');
        if (!container) return;

        container.innerHTML = '';
        const fragment = document.createDocumentFragment();
        
        this.connections.forEach(conn => {
            const fromP = this.processManager.getProcess(conn.fromId);
            const toP = this.processManager.getProcess(conn.toId);
            if (!fromP || !toP) return;

            const el = document.createElement('div');
            el.className = 'connection-item';
            el.innerHTML = `
        <span class="conn-type ${conn.type}">${conn.type}</span>
        <span>${fromP.name}</span>
        <span class="conn-arrow">→</span>
        <span>${toP.name}</span>
      `;
            fragment.appendChild(el);
        });
        
        container.appendChild(fragment);
    }
}

// ----- Initialize when DOM is ready -----
document.addEventListener('DOMContentLoaded', () => {
    const app = new App();
    app.init();
});
