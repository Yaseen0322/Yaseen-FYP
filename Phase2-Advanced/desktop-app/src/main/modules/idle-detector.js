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
        
        this.isRunning = false;
        this.isPaused = false;
        this.timer = null;
        
        this.isIdle = false;
        this.idleStart = null;
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
                // Get system idle time in seconds
                const idleSeconds = powerMonitor.getSystemIdleTime();
                
                if (idleSeconds >= this.idleThreshold) {
                    // User is idle
                    if (!this.isIdle) {
                        // Transition to idle state
                        this.isIdle = true;
                        // Idle started (threshold seconds ago)
                        this.idleStart = new Date(Date.now() - (this.idleThreshold * 1000));
                        console.log('[IdleDetector] User went idle');
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
            const durationMs = endTime - this.idleStart;
            const durationSec = Math.floor(durationMs / 1000);
            
            // Only save if duration >= threshold
            if (durationSec >= this.idleThreshold) {
                const record = {
                    start_ts: this.idleStart.toISOString(),
                    end_ts: endTime.toISOString(),
                    duration_sec: durationSec
                };
                
                this.localStorage.saveIdleInterval(record);
            }
            
            this.isIdle = false;
            this.idleStart = null;
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
