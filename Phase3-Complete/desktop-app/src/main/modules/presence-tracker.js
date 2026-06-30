/**
 * Presence Tracker Module
 * Polls webcam-service status and stores presence intervals locally.
 */
const axios = require('axios');

class PresenceTracker {
    constructor(localStorage, options = {}) {
        this.localStorage = localStorage;
        this.statusUrl = options.statusUrl || 'http://127.0.0.1:8001/status';
        this.pollInterval = options.pollInterval || 10000; // 10s
        this.currentPollInterval = this.pollInterval;
        this.cameraOffStreak = 0;

        this.isRunning = false;
        this.isPaused = false;
        this.timer = null;

        this.currentState = null;
        this.currentStateStart = null;
    }

    start() {
        if (this.isRunning) return;
        this.isRunning = true;
        this.isPaused = false;
        this.poll();
        console.log('[PresenceTracker] Started');
    }

    stop() {
        if (!this.isRunning) return;
        this.isRunning = false;
        if (this.timer) {
            clearTimeout(this.timer);
            this.timer = null;
        }
        this.finalizeCurrentState();
        console.log('[PresenceTracker] Stopped');
    }

    pause() {
        this.isPaused = true;
        this.finalizeCurrentState();
        console.log('[PresenceTracker] Paused');
    }

    resume() {
        this.isPaused = false;
        console.log('[PresenceTracker] Resumed');
    }

    async poll() {
        if (!this.isRunning) return;

        if (!this.isPaused) {
            const nextState = await this.fetchPresenceState();

            if (nextState !== this.currentState) {
                this.finalizeCurrentState();
                this.currentState = nextState;
                this.currentStateStart = new Date();
            }

            if (nextState === 'camera_off') {
                this.cameraOffStreak += 1;
                if (this.cameraOffStreak >= 3) {
                    this.currentPollInterval = Math.min(this.pollInterval * 3, this.currentPollInterval + this.pollInterval);
                }
            } else {
                this.cameraOffStreak = 0;
                this.currentPollInterval = this.pollInterval;
            }
        }

        this.timer = setTimeout(() => this.poll(), this.currentPollInterval);
    }

    async fetchPresenceState() {
        try {
            const response = await axios.get(this.statusUrl, { timeout: 4000 });
            const state = response?.data?.state;
            if (state === 'present' || state === 'absent' || state === 'camera_off') {
                return state;
            }
        } catch (error) {
            // Treat service unavailability as camera_off to preserve continuity.
        }
        return 'camera_off';
    }

    finalizeCurrentState() {
        if (!this.currentState || !this.currentStateStart) return;

        const end = new Date();
        this.savePresenceInterval(this.currentStateStart, end);

        this.currentState = null;
        this.currentStateStart = null;
    }

    flushOpenInterval() {
        if (!this.currentState || !this.currentStateStart) return;

        const end = new Date();
        if (this.savePresenceInterval(this.currentStateStart, end)) {
            this.currentStateStart = end;
        }
    }

    savePresenceInterval(start, end) {
        const durationSec = Math.floor((end - start) / 1000);

        if (durationSec >= 1) {
            this.localStorage.savePresenceInterval({
                state: this.currentState,
                start_ts: start.toISOString(),
                end_ts: end.toISOString(),
                duration_sec: durationSec
            });
            return true;
        }
        return false;
    }

    getStats() {
        return {
            isRunning: this.isRunning,
            isPaused: this.isPaused,
            currentState: this.currentState,
            stateSince: this.currentStateStart,
            pollInterval: this.currentPollInterval
        };
    }
}

module.exports = { PresenceTracker };
