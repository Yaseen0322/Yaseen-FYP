/**
 * Data Sync Module
 * Syncs local tracking data to backend server
 */
const axios = require('axios');
const Store = require('electron-store');

class DataSync {
    constructor(localStorage, authToken, options = {}) {
        this.localStorage = localStorage;
        this.authToken = authToken;
        this.baseUrl = options.baseUrl || 'http://localhost:8000/api/v1';
        this.syncInterval = options.syncInterval || 60000; // 1 minute
        
        this.isRunning = false;
        this.timer = null;
        
        this.store = new Store();
        this.deviceId = this.store.get('deviceId');
    }

    start() {
        if (this.isRunning) return;
        
        this.isRunning = true;
        this.sync();
        
        console.log('[DataSync] Started');
    }

    stop() {
        this.isRunning = false;
        if (this.timer) {
            clearTimeout(this.timer);
            this.timer = null;
        }
        
        console.log('[DataSync] Stopped');
    }

    async sync() {
        if (!this.isRunning) return;
        
        if (!this.deviceId) {
            console.log('[DataSync] No device ID, skipping sync');
            this.scheduleNext();
            return;
        }
        
        try {
            // Sync app usage
            await this.syncAppUsage();
            
            // Sync idle intervals
            await this.syncIdleIntervals();
            
            // Sync presence intervals
            await this.syncPresenceIntervals();
            
            // Sync browser usage
            await this.syncBrowserUsage();
            
            // Update last sync time
            this.localStorage.setLastSyncTime(new Date().toISOString());
            
            console.log('[DataSync] Sync completed');
        } catch (error) {
            console.error('[DataSync] Sync error:', error.message);
        }
        
        this.scheduleNext();
    }

    scheduleNext() {
        if (this.isRunning) {
            this.timer = setTimeout(() => this.sync(), this.syncInterval);
        }
    }

    async syncAppUsage() {
        const records = this.localStorage.getUnsyncdAppUsage();
        if (records.length === 0) return;
        
        const items = records.map(r => ({
            device_id: this.deviceId,
            app_name: r.app_name,
            window_title: r.window_title,
            start_ts: r.start_ts,
            end_ts: r.end_ts,
            duration_sec: r.duration_sec
        }));
        
        try {
            await axios.post(
                `${this.baseUrl}/ingest/app-usage`,
                { items },
                { headers: this.getHeaders() }
            );
            
            this.localStorage.markAppUsageSynced(records.map(r => r.id));
            console.log(`[DataSync] Synced ${records.length} app usage records`);
        } catch (error) {
            console.error('[DataSync] App usage sync failed:', error.message);
        }
    }

    async syncIdleIntervals() {
        const records = this.localStorage.getUnsyncdIdleIntervals();
        if (records.length === 0) return;
        
        const items = records.map(r => ({
            device_id: this.deviceId,
            start_ts: r.start_ts,
            end_ts: r.end_ts,
            duration_sec: r.duration_sec
        }));
        
        try {
            await axios.post(
                `${this.baseUrl}/ingest/idle-intervals`,
                { items },
                { headers: this.getHeaders() }
            );
            
            this.localStorage.markIdleIntervalsSynced(records.map(r => r.id));
            console.log(`[DataSync] Synced ${records.length} idle intervals`);
        } catch (error) {
            console.error('[DataSync] Idle intervals sync failed:', error.message);
        }
    }

    async syncPresenceIntervals() {
        const records = this.localStorage.getUnsyncdPresenceIntervals();
        if (records.length === 0) return;
        
        const items = records.map(r => ({
            device_id: this.deviceId,
            state: r.state,
            start_ts: r.start_ts,
            end_ts: r.end_ts,
            duration_sec: r.duration_sec
        }));
        
        try {
            await axios.post(
                `${this.baseUrl}/ingest/presence-intervals`,
                { items },
                { headers: this.getHeaders() }
            );
            
            this.localStorage.markPresenceIntervalsSynced(records.map(r => r.id));
            console.log(`[DataSync] Synced ${records.length} presence intervals`);
        } catch (error) {
            console.error('[DataSync] Presence intervals sync failed:', error.message);
        }
    }

    async syncBrowserUsage() {
        const records = this.localStorage.getUnsyncdBrowserUsage();
        if (records.length === 0) return;
        
        const items = records.map(r => ({
            device_id: this.deviceId,
            browser: r.browser,
            domain: r.domain,
            start_ts: r.start_ts,
            end_ts: r.end_ts,
            duration_sec: r.duration_sec
        }));
        
        try {
            await axios.post(
                `${this.baseUrl}/ingest/browser-usage`,
                { items },
                { headers: this.getHeaders() }
            );
            
            this.localStorage.markBrowserUsageSynced(records.map(r => r.id));
            console.log(`[DataSync] Synced ${records.length} browser usage records`);
        } catch (error) {
            console.error('[DataSync] Browser usage sync failed:', error.message);
        }
    }

    getHeaders() {
        return {
            'Authorization': `Bearer ${this.authToken}`,
            'Content-Type': 'application/json'
        };
    }

    updateToken(newToken) {
        this.authToken = newToken;
    }
}

module.exports = { DataSync };
