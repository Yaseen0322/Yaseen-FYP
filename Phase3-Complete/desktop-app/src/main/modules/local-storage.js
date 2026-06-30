/**
 * Local Storage Module
 * Stores tracking data locally in an Electron Store namespace per user
 * so queued telemetry cannot leak across authenticated sessions.
 */
const Store = require('electron-store');

class LocalStorage {
    constructor(namespace = 'default') {
        this.namespace = this.normalizeNamespace(namespace);
        this.store = new Store({
            name: `tracking-data-${this.namespace}`,
            defaults: {
                appUsage: [],
                idleIntervals: [],
                presenceIntervals: [],
                browserUsage: [],
                lastSyncTime: null
            }
        });
        
        // Batch size for sync
        this.batchSize = 100;
        
        console.log(`[LocalStorage] Initialized namespace=${this.namespace}`);
    }

    // App Usage
    saveAppUsage(record) {
        const records = this.store.get('appUsage', []);
        const merged = this.mergeWithLast(records, record, {
            keys: ['app_name', 'window_title'],
            maxGapSeconds: 3
        });
        if (!merged) {
            records.push({
                ...record,
                id: this.createRecordId(),
                synced: false
            });
        }
        this.store.set('appUsage', records);
    }

    getUnsyncdAppUsage() {
        const records = this.store.get('appUsage', []);
        return records.filter(r => !r.synced).slice(0, this.batchSize);
    }

    markAppUsageSynced(ids) {
        const records = this.store.get('appUsage', []);
        const updated = records.map(r => 
            ids.includes(r.id) ? { ...r, synced: true } : r
        );
        this.store.set('appUsage', updated);
        
        // Clean up old synced records (keep last 1000)
        this.cleanupSyncedRecords('appUsage');
    }

    // Idle Intervals
    saveIdleInterval(record) {
        const records = this.store.get('idleIntervals', []);
        const merged = this.mergeWithLast(records, record, {
            keys: [],
            maxGapSeconds: 3
        });
        if (!merged) {
            records.push({
                ...record,
                id: this.createRecordId(),
                synced: false
            });
        }
        this.store.set('idleIntervals', records);
    }

    getUnsyncdIdleIntervals() {
        const records = this.store.get('idleIntervals', []);
        return records.filter(r => !r.synced).slice(0, this.batchSize);
    }

    markIdleIntervalsSynced(ids) {
        const records = this.store.get('idleIntervals', []);
        const updated = records.map(r => 
            ids.includes(r.id) ? { ...r, synced: true } : r
        );
        this.store.set('idleIntervals', updated);
        this.cleanupSyncedRecords('idleIntervals');
    }

    // Presence Intervals
    savePresenceInterval(record) {
        const records = this.store.get('presenceIntervals', []);
        const merged = this.mergeWithLast(records, record, {
            keys: ['state'],
            maxGapSeconds: 3
        });
        if (!merged) {
            records.push({
                ...record,
                id: this.createRecordId(),
                synced: false
            });
        }
        this.store.set('presenceIntervals', records);
    }

    getUnsyncdPresenceIntervals() {
        const records = this.store.get('presenceIntervals', []);
        return records.filter(r => !r.synced).slice(0, this.batchSize);
    }

    markPresenceIntervalsSynced(ids) {
        const records = this.store.get('presenceIntervals', []);
        const updated = records.map(r => 
            ids.includes(r.id) ? { ...r, synced: true } : r
        );
        this.store.set('presenceIntervals', updated);
        this.cleanupSyncedRecords('presenceIntervals');
    }

    // Browser Usage
    saveBrowserUsage(record) {
        const records = this.store.get('browserUsage', []);
        const merged = this.mergeWithLast(records, record, {
            keys: ['browser', 'domain'],
            maxGapSeconds: 3
        });
        if (!merged) {
            records.push({
                ...record,
                id: this.createRecordId(),
                synced: false
            });
        }
        this.store.set('browserUsage', records);
    }

    getUnsyncdBrowserUsage() {
        const records = this.store.get('browserUsage', []);
        return records.filter(r => !r.synced).slice(0, this.batchSize);
    }

    markBrowserUsageSynced(ids) {
        const records = this.store.get('browserUsage', []);
        const updated = records.map(r => 
            ids.includes(r.id) ? { ...r, synced: true } : r
        );
        this.store.set('browserUsage', updated);
        this.cleanupSyncedRecords('browserUsage');
    }

    // Cleanup
    cleanupSyncedRecords(key) {
        const records = this.store.get(key, []);
        const synced = records.filter(r => r.synced);
        const unsynced = records.filter(r => !r.synced);
        
        // Keep only last 500 synced records + all unsynced
        const toKeep = [...synced.slice(-500), ...unsynced];
        this.store.set(key, toKeep);
    }

    // Stats
    getStats() {
        return {
            appUsage: {
                total: this.store.get('appUsage', []).length,
                unsynced: this.store.get('appUsage', []).filter(r => !r.synced).length
            },
            idleIntervals: {
                total: this.store.get('idleIntervals', []).length,
                unsynced: this.store.get('idleIntervals', []).filter(r => !r.synced).length
            },
            presenceIntervals: {
                total: this.store.get('presenceIntervals', []).length,
                unsynced: this.store.get('presenceIntervals', []).filter(r => !r.synced).length
            },
            browserUsage: {
                total: this.store.get('browserUsage', []).length,
                unsynced: this.store.get('browserUsage', []).filter(r => !r.synced).length
            },
            lastSyncTime: this.store.get('lastSyncTime')
        };
    }

    setLastSyncTime(time) {
        this.store.set('lastSyncTime', time);
    }

    clearAll() {
        this.store.clear();
    }

    getUnsyncedCounts() {
        const appUsage = this.store.get('appUsage', []);
        const idleIntervals = this.store.get('idleIntervals', []);
        const presenceIntervals = this.store.get('presenceIntervals', []);
        const browserUsage = this.store.get('browserUsage', []);

        return {
            appUsage: appUsage.filter(r => !r.synced).length,
            idleIntervals: idleIntervals.filter(r => !r.synced).length,
            presenceIntervals: presenceIntervals.filter(r => !r.synced).length,
            browserUsage: browserUsage.filter(r => !r.synced).length
        };
    }

    createRecordId() {
        return Date.now() + Math.floor(Math.random() * 1000);
    }

    mergeWithLast(records, nextRecord, options = {}) {
        if (!records.length) return false;

        const last = records[records.length - 1];
        if (!last || last.synced) return false;

        const keys = options.keys || [];
        for (const key of keys) {
            if (last[key] !== nextRecord[key]) return false;
        }

        const lastEnd = Date.parse(last.end_ts);
        const nextStart = Date.parse(nextRecord.start_ts);
        const nextEnd = Date.parse(nextRecord.end_ts);
        if (!Number.isFinite(lastEnd) || !Number.isFinite(nextStart) || !Number.isFinite(nextEnd)) {
            return false;
        }

        const gapSeconds = Math.floor((nextStart - lastEnd) / 1000);
        const maxGapSeconds = options.maxGapSeconds ?? 0;
        if (gapSeconds < 0 || gapSeconds > maxGapSeconds) return false;

        const mergedDuration = Math.max(1, Math.floor((nextEnd - Date.parse(last.start_ts)) / 1000));
        last.end_ts = nextRecord.end_ts;
        last.duration_sec = mergedDuration;
        return true;
    }

    normalizeNamespace(value) {
        return String(value || 'default')
            .replace(/[^a-zA-Z0-9_-]/g, '-')
            .replace(/-+/g, '-')
            .replace(/^-|-$/g, '') || 'default';
    }
}

module.exports = { LocalStorage };
