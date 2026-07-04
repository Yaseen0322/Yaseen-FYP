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
        this.baseUrl = options.baseUrl || 'http://127.0.0.1:8000/api/v1';
        this.syncInterval = options.syncInterval || 60000; // 1 minute
        this.onSyncComplete = typeof options.onSyncComplete === 'function' ? options.onSyncComplete : null;
        this.onSyncError = typeof options.onSyncError === 'function' ? options.onSyncError : null;
        this.beforeSync = typeof options.beforeSync === 'function' ? options.beforeSync : null;
        this.request = typeof options.request === 'function' ? options.request : null;
        
        this.isRunning = false;
        this.timer = null;
        
        this.store = new Store();
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
        
        const deviceId = this.getDeviceId();
        if (!deviceId) {
            console.log('[DataSync] No device ID, skipping sync');
            this.scheduleNext();
            return;
        }

        if (this.beforeSync) {
            try {
                this.beforeSync();
            } catch (error) {
                console.error('[DataSync] Pre-sync flush failed:', error.message);
            }
        }
        
        const counts = this.localStorage.getUnsyncedCounts
            ? this.localStorage.getUnsyncedCounts()
            : null;
        const pendingTotal = counts
            ? (counts.appUsage + counts.idleIntervals + counts.presenceIntervals + counts.browserUsage)
            : null;

        if (pendingTotal === 0) {
            this.scheduleNext();
            return;
        }

        try {
            // Sync app usage
            const appCount = await this.syncAppUsage();
            
            // Sync idle intervals
            const idleCount = await this.syncIdleIntervals();
            
            // Sync presence intervals
            const presenceCount = await this.syncPresenceIntervals();
            
            // Sync browser usage
            const browserCount = await this.syncBrowserUsage();
            
            // Update last sync time
            const syncedAt = new Date().toISOString();
            this.localStorage.setLastSyncTime(syncedAt);

            const totalSynced = appCount + idleCount + presenceCount + browserCount;
            if (this.onSyncComplete && totalSynced > 0) {
                this.onSyncComplete({
                    synced_at: syncedAt,
                    app_usage_count: appCount,
                    idle_count: idleCount,
                    presence_count: presenceCount,
                    browser_count: browserCount,
                    total_synced: totalSynced
                });
            }
            
            console.log('[DataSync] Sync completed');
        } catch (error) {
            console.error('[DataSync] Sync error:', error.message);
            if (this.onSyncError) {
                this.onSyncError(error);
            }
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
        if (records.length === 0) return 0;
        
        const items = records.map(r => ({
            device_id: this.getDeviceId(),
            app_name: r.app_name,
            window_title: r.window_title,
            start_ts: r.start_ts,
            end_ts: r.end_ts,
            duration_sec: r.duration_sec
        }));
        
        try {
            await this.post('/ingest/app-usage', { items });
            
            this.localStorage.markAppUsageSynced(records.map(r => r.id));
            console.log(`[DataSync] Synced ${records.length} app usage records`);
        } catch (error) {
            console.error('[DataSync] App usage sync failed:', error.message);
            return 0;
        }
        return records.length;
    }

    async syncIdleIntervals() {
        const records = this.localStorage.getUnsyncdIdleIntervals();
        if (records.length === 0) return 0;
        
        const items = records.map(r => ({
            device_id: this.getDeviceId(),
            start_ts: r.start_ts,
            end_ts: r.end_ts,
            duration_sec: r.duration_sec
        }));
        
        try {
            await this.post('/ingest/idle-intervals', { items });
            
            this.localStorage.markIdleIntervalsSynced(records.map(r => r.id));
            console.log(`[DataSync] Synced ${records.length} idle intervals`);
        } catch (error) {
            console.error('[DataSync] Idle intervals sync failed:', error.message);
            return 0;
        }
        return records.length;
    }

    async syncPresenceIntervals() {
        const records = this.localStorage.getUnsyncdPresenceIntervals();
        if (records.length === 0) return 0;
        
        const items = records.map(r => ({
            device_id: this.getDeviceId(),
            state: r.state,
            start_ts: r.start_ts,
            end_ts: r.end_ts,
            duration_sec: r.duration_sec
        }));
        
        try {
            await this.post('/ingest/presence-intervals', { items });
            
            this.localStorage.markPresenceIntervalsSynced(records.map(r => r.id));
            console.log(`[DataSync] Synced ${records.length} presence intervals`);
        } catch (error) {
            console.error('[DataSync] Presence intervals sync failed:', error.message);
            return 0;
        }
        return records.length;
    }

    async syncBrowserUsage() {
        const records = this.localStorage.getUnsyncdBrowserUsage();
        if (records.length === 0) return 0;
        
        const items = records.map(r => ({
            device_id: this.getDeviceId(),
            browser: r.browser,
            domain: r.domain,
            start_ts: r.start_ts,
            end_ts: r.end_ts,
            duration_sec: r.duration_sec
        }));
        
        try {
            await this.post('/ingest/browser-usage', { items });
            
            this.localStorage.markBrowserUsageSynced(records.map(r => r.id));
            console.log(`[DataSync] Synced ${records.length} browser usage records`);
        } catch (error) {
            console.error('[DataSync] Browser usage sync failed:', error.message);
            return 0;
        }
        return records.length;
    }

    async post(path, data) {
        const url = `${this.baseUrl}${path}`;
        if (this.request) {
            return this.request({
                method: 'post',
                url,
                data,
                timeout: 10000
            });
        }

        return axios.post(url, data, { headers: this.getHeaders(), timeout: 10000 });
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

    getDeviceId() {
        const deviceId = this.store.get('deviceId');
        return Number.isFinite(deviceId) ? deviceId : null;
    }

    setSyncInterval(intervalMs) {
        if (!Number.isFinite(intervalMs)) return;
        const normalized = Math.max(10000, Math.floor(intervalMs));
        this.syncInterval = normalized;
    }

    async syncNow() {
        await this.sync();
    }
}

module.exports = { DataSync };
