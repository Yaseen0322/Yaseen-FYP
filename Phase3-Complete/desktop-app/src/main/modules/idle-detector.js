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
    }

    start() {
        if (this.isRunning) return;
        
        this.isRunning = true;
        this.isPaused = false;
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
                        this.isIdle = true;
                        // When idle_time is unavailable, use current time as conservative start.
                        const backfillSec = idleByTime ? this.idleThreshold : 0;
                        this.idleStart = new Date(Date.now() - (backfillSec * 1000));
                        this.lastFlushedAt = this.idleStart;
                        this.lastIdleSignalAt = new Date();
                        console.log('[IdleDetector] User went idle');
                    } else {
                        this.lastIdleSignalAt = new Date();
                        // Persist partial idle so reports update while still idle.
                        this.flushIdleChunk();
                    }
                } else {
                    // User is active
                    if (this.isIdle) {
                        // Was idle, now active - finalize interval
                        this.finalizeIdleInterval();
                        console.log('[IdleDetector] User became active');
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

    flushIdleChunk() {
        if (!this.isIdle || !this.lastFlushedAt) return;

        const now = new Date();
        const chunkSec = Math.floor((now - this.lastFlushedAt) / 1000);
        if (chunkSec >= this.chunkFlushInterval) {
            this.saveIdleInterval(this.lastFlushedAt, now);
            this.lastFlushedAt = now;
        }
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
            idleSince: this.idleStart,
            idleThreshold: this.idleThreshold
        };
    }
}

module.exports = { IdleDetector };
