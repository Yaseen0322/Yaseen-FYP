/**
 * Activity Tracker Module
 * Tracks active window/application focus time
 * Privacy: Only app names stored, window titles optional and configurable
 */
const activeWin = require('active-win');

class ActivityTracker {
    constructor(localStorage, options = {}) {
        this.localStorage = localStorage;
        this.interval = options.interval || 2000; // Check every 2 seconds
        this.storeWindowTitle = options.storeWindowTitle || false;
        
        this.isRunning = false;
        this.isPaused = false;
        this.timer = null;
        
        this.currentApp = null;
        this.currentAppStart = null;
    }

    start() {
        if (this.isRunning) return;
        
        this.isRunning = true;
        this.isPaused = false;
        this.track();
        
        console.log('[ActivityTracker] Started');
    }

    stop() {
        if (!this.isRunning) return;
        
        this.isRunning = false;
        if (this.timer) {
            clearTimeout(this.timer);
            this.timer = null;
        }
        
        // Save final interval
        this.finalizeCurrentApp();
        
        console.log('[ActivityTracker] Stopped');
    }

    pause() {
        this.isPaused = true;
        this.finalizeCurrentApp();
        console.log('[ActivityTracker] Paused');
    }

    resume() {
        this.isPaused = false;
        console.log('[ActivityTracker] Resumed');
    }

    async track() {
        if (!this.isRunning) return;
        
        if (!this.isPaused) {
            try {
                const window = await activeWin();
                
                if (window) {
                    const appName = window.owner?.name || 'Unknown';
                    
                    // Check if app changed
                    if (this.currentApp !== appName) {
                        this.finalizeCurrentApp();
                        
                        // Start new app tracking
                        this.currentApp = appName;
                        this.currentAppStart = new Date();
                        this.currentWindowTitle = this.storeWindowTitle ? window.title : null;
                    }
                }
            } catch (error) {
                console.error('[ActivityTracker] Error:', error.message);
            }
        }
        
        // Schedule next check
        this.timer = setTimeout(() => this.track(), this.interval);
    }

    finalizeCurrentApp() {
        if (this.currentApp && this.currentAppStart) {
            const endTime = new Date();
            const durationMs = endTime - this.currentAppStart;
            const durationSec = Math.floor(durationMs / 1000);
            
            // Only save if duration > 1 second
            if (durationSec >= 1) {
                const record = {
                    app_name: this.currentApp,
                    window_title: this.currentWindowTitle,
                    start_ts: this.currentAppStart.toISOString(),
                    end_ts: endTime.toISOString(),
                    duration_sec: durationSec
                };
                
                this.localStorage.saveAppUsage(record);
            }
            
            this.currentApp = null;
            this.currentAppStart = null;
            this.currentWindowTitle = null;
        }
    }

    getStats() {
        return {
            isRunning: this.isRunning,
            isPaused: this.isPaused,
            currentApp: this.currentApp,
            trackingSince: this.currentAppStart
        };
    }

    setStoreWindowTitle(enabled) {
        this.storeWindowTitle = !!enabled;
    }
}

module.exports = { ActivityTracker };
