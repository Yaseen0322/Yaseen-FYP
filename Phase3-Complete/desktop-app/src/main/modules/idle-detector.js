/**
 * Idle Detector Module
 * Detects keyboard/mouse inactivity
 * Privacy: Only tracks idle intervals, no keystroke content
 */
const { powerMonitor } = require('electron');

class IdleDetector {
    constructor(localStorage, options = {}) {
        this.localStorage = localStorage;
        this.idleThreshold = options.idleThreshold || 120; // 2 minutes in seconds
        this.checkInterval = options.checkInterval || 5000; // Check every 5 seconds
        this.chunkFlushInterval = options.chunkFlushInterval || 30; // Persist open idle every 30 seconds
        
        this.isRunning = false;
        this.isPaused = false;
        this.timer = null;
        
        this.isIdle = false;
        this.idleStart = null;
        this.lastFlushedAt = null;
        this.lastIdleSignalAt = null;
        this.powerMonitorHandlers = [];
    }

    start() {
        if (this.isRunning) return;
        
        this.isRunning = true;
        this.isPaused = false;
        this.registerPowerMonitorEvents();
        this.check();
        
        console.log('[IdleDetector] Started with threshold:', this.idleThreshold, 'seconds');
    }

    stop() {
        if (!this.isRunning) return;
        
        this.isRunning = false;
        if (this.timer) {
            clearTimeout(this.timer);
            this.timer = null;
        }
        this.unregisterPowerMonitorEvents();
        
        // Save final idle interval if any
        this.finalizeIdleInterval();
        
        console.log('[IdleDetector] Stopped');
    }

    pause() {
        this.isPaused = true;
        this.finalizeIdleInterval();
        console.log('[IdleDetector] Paused');
    }

    resume() {
        this.isPaused = false;
        console.log('[IdleDetector] Resumed');
    }

    registerPowerMonitorEvents() {
        if (this.powerMonitorHandlers.length > 0) return;

        const handlers = [
            ['lock-screen', () => this.enterIdle(0)],
            ['suspend', () => this.enterIdle(0)],
            ['user-did-resign-active', () => this.enterIdle(0)],
            ['unlock-screen', () => this.exitIdle()],
            ['resume', () => this.exitIdle()],
            ['user-did-become-active', () => this.exitIdle()],
        ];

        for (const [eventName, handler] of handlers) {
            try {
                powerMonitor.on(eventName, handler);
                this.powerMonitorHandlers.push([eventName, handler]);
            } catch (_) {
                // Some platforms do not emit every event; polling remains active.
            }
        }
    }

    unregisterPowerMonitorEvents() {
        for (const [eventName, handler] of this.powerMonitorHandlers) {
            try {
                powerMonitor.removeListener(eventName, handler);
            } catch (_) {
                // Ignore platform-specific event removal issues.
            }
        }
        this.powerMonitorHandlers = [];
    }

    enterIdle(backfillSec = 0) {
        if (!this.isRunning || this.isPaused || this.isIdle) return;

        const normalizedBackfill = Math.max(0, Math.floor(backfillSec || 0));
        this.isIdle = true;
        this.idleStart = new Date(Date.now() - (normalizedBackfill * 1000));
        this.lastFlushedAt = this.idleStart;
        this.lastIdleSignalAt = new Date();
        console.log('[IdleDetector] User went idle');
    }

    exitIdle() {
        if (!this.isRunning || !this.isIdle) return;
        this.finalizeIdleInterval();
        console.log('[IdleDetector] User became active');
    }

    check() {
        if (!this.isRunning) return;
        
        if (!this.isPaused) {
            try {
                const idleSeconds = this.getIdleSeconds();
                const idleState = this.getIdleState();
                const idleByTime = typeof idleSeconds === 'number' && idleSeconds >= this.idleThreshold;
                const idleByState = idleState === 'idle' || idleState === 'locked';

                if (idleByTime || idleByState) {
                    // User is idle
                    if (!this.isIdle) {
                        // Transition to idle state
                        // When idle_time is unavailable, use current time as conservative start.
                        const backfillSec = idleByTime ? this.idleThreshold : 0;
                        this.enterIdle(backfillSec);
                    } else {
                        this.lastIdleSignalAt = new Date();
                        // Persist partial idle so reports update while still idle.
                        this.flushIdleChunk();
                    }
                } else {
                    // User is active
                    if (this.isIdle) {
                        // Was idle, now active - finalize interval
                        this.exitIdle();
                    }
                }
            } catch (error) {
                console.error('[IdleDetector] Error:', error.message);
            }
        }
        
        // Schedule next check
        this.timer = setTimeout(() => this.check(), this.checkInterval);
    }

    finalizeIdleInterval() {
        if (this.isIdle && this.idleStart) {
            const endTime = new Date();
            this.saveIdleInterval(this.lastFlushedAt || this.idleStart, endTime);
            
            this.isIdle = false;
            this.idleStart = null;
            this.lastFlushedAt = null;
        }
    }

    flushIdleChunk(force = false) {
        if (!this.isIdle || !this.lastFlushedAt) return;

        const now = new Date();
        const chunkSec = Math.floor((now - this.lastFlushedAt) / 1000);
        if (chunkSec >= (force ? 1 : this.chunkFlushInterval)) {
            this.saveIdleInterval(this.lastFlushedAt, now);
            this.lastFlushedAt = now;
        }
    }

    flushOpenInterval() {
        this.flushIdleChunk(true);
    }

    saveIdleInterval(startTime, endTime) {
        if (!startTime || !endTime || endTime <= startTime) return;
        const durationSec = Math.floor((endTime - startTime) / 1000);
        if (durationSec < 1) return;

        const record = {
            start_ts: startTime.toISOString(),
            end_ts: endTime.toISOString(),
            duration_sec: durationSec
        };

        this.localStorage.saveIdleInterval(record);
    }

    getIdleSeconds() {
        try {
            const idleSeconds = powerMonitor.getSystemIdleTime();
            return Number.isFinite(idleSeconds) && idleSeconds >= 0 ? idleSeconds : null;
        } catch (_) {
            return null;
        }
    }

    getIdleState() {
        try {
            return powerMonitor.getSystemIdleState(this.idleThreshold);
        } catch (_) {
            return null;
        }
    }

    getStats() {
        return {
            isRunning: this.isRunning,
            isPaused: this.isPaused,
            isIdle: this.isIdle,
            idleSince: this.lastFlushedAt || this.idleStart,
            idleThreshold: this.idleThreshold
        };
    }

    setIdleThreshold(seconds) {
        if (!Number.isFinite(seconds)) return;
        const normalized = Math.max(30, Math.min(600, Math.floor(seconds)));
        this.idleThreshold = normalized;
    }
}

module.exports = { IdleDetector };
