/**
 * Preload Script
 * Exposes secure APIs to renderer process
 */
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
    // Auth
    login: (email, password) => ipcRenderer.invoke('auth:login', { email, password }),
    logout: () => ipcRenderer.invoke('auth:logout'),
    getUser: () => ipcRenderer.invoke('auth:getUser'),
    isLoggedIn: () => ipcRenderer.invoke('auth:isLoggedIn'),
    
    // Device
    registerDevice: () => ipcRenderer.invoke('device:register'),
    
    // Tracking
    getTrackingStatus: () => ipcRenderer.invoke('tracking:getStatus'),
    pauseTracking: () => ipcRenderer.invoke('tracking:pause'),
    resumeTracking: () => ipcRenderer.invoke('tracking:resume'),
    syncNow: () => ipcRenderer.invoke('sync:now'),
    
    // Reports
    getTodaySummary: () => ipcRenderer.invoke('reports:getTodaySummary'),
    getTimeline: (date) => ipcRenderer.invoke('reports:getTimeline', date),
    getWeekly: (weekOffset) => ipcRenderer.invoke('reports:getWeekly', weekOffset),
    
    // Settings
    getSetting: (key) => ipcRenderer.invoke('settings:get', key),
    setSetting: (key, value) => ipcRenderer.invoke('settings:set', key, value),
    
    // Events
    onTrackingUpdate: (callback) => {
        const listener = (event, data) => callback(data);
        ipcRenderer.on('tracking:update', listener);
        return () => ipcRenderer.removeListener('tracking:update', listener);
    },
    onSyncComplete: (callback) => {
        const listener = (event, data) => callback(data);
        ipcRenderer.on('sync:complete', listener);
        return () => ipcRenderer.removeListener('sync:complete', listener);
    }
});
