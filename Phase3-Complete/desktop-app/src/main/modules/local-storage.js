/**
 * Local Storage Module
 * Stores tracking data locally in SQLite for offline support
 */
const Store = require('electron-store');
const path = require('path');
const fs = require('fs');

class LocalStorage {
    constructor() {
        this.store = new Store({
            name: 'tracking-data',
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
        
        console.log('[LocalStorage] Initialized');
    }

    // App Usage
    saveAppUsage(record) {
        const records = this.store.get('appUsage', []);
        records.push({
            ...record,
            id: Date.now(),
            synced: false
        });
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
        records.push({
            ...record,
            id: Date.now(),
            synced: false
        });
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
        records.push({
            ...record,
            id: Date.now(),
            synced: false
        });
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
        records.push({
            ...record,
            id: Date.now(),
            synced: false
        });
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
}

module.exports = { LocalStorage };
