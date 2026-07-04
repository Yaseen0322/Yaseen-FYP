/**
 * Electron Main Process
 * Handles: window management, system tray, activity tracking, IPC
 */
const { app, BrowserWindow, Tray, Menu, ipcMain, nativeImage } = require('electron');
const fs = require('fs');
const path = require('path');
const { ActivityTracker } = require('./modules/activity-tracker');
const { IdleDetector } = require('./modules/idle-detector');
const { PresenceTracker } = require('./modules/presence-tracker');
const { DataSync } = require('./modules/data-sync');
const { BrowserUsageServer } = require('./modules/browser-usage-server');
const { LocalStorage } = require('./modules/local-storage');
const {
    buildLocalDailySummary,
    buildLocalTimeline,
    getLocalDateString,
    mergeSummaries,
    mergeTimelines
} = require('./modules/local-reports');
const Store = require('electron-store');
const axios = require('axios');

// Store for app settings and auth
const store = new Store();
const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

let mainWindow = null;
let tray = null;
let activityTracker = null;
let idleDetector = null;
let presenceTracker = null;
let dataSync = null;
let localStorage = null;
let browserUsageServer = null;
let trackingUpdateTimer = null;

const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;

function getApiBaseUrl() {
    return store.get('apiBaseUrl', DEFAULT_API_BASE_URL);
}

function apiUrl(path) {
    return `${getApiBaseUrl()}${path}`;
}

function getSyncIntervalMs() {
    // `syncInterval` is stored in seconds in settings UI.
    const raw = store.get('syncInterval', 10);
    if (!Number.isFinite(raw)) return 60000;

    // Backward compatibility: old value may be stored in milliseconds.
    if (raw > 1000) {
        const seconds = Math.max(10, Math.floor(raw / 1000));
        store.set('syncInterval', seconds);
        return seconds * 1000;
    }

    const seconds = Math.max(10, Math.floor(raw));
    return seconds * 1000;
}

function getAssetPath(...segments) {
    const assetPath = path.join(__dirname, '../../assets', ...segments);
    return fs.existsSync(assetPath) ? assetPath : null;
}

function createFallbackIcon() {
    const svg = `
        <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">
            <rect width="32" height="32" rx="7" fill="#0f766e"/>
            <path d="M9 11h14v3H9zm0 7h9v3H9z" fill="#ecfeff"/>
        </svg>
    `;
    return nativeImage.createFromDataURL(
        `data:image/svg+xml;base64,${Buffer.from(svg).toString('base64')}`
    );
}

function getWindowIcon() {
    const iconPath = getAssetPath('icon.png');
    return iconPath || undefined;
}

function getTrayIcon() {
    const trayIconPath = getAssetPath('tray-icon.png') || getAssetPath('icon.png');
    return trayIconPath ? nativeImage.createFromPath(trayIconPath) : createFallbackIcon();
}

function isTrackingActive() {
    return !!(
        activityTracker?.isRunning &&
        !activityTracker?.isPaused &&
        idleDetector?.isRunning &&
        !idleDetector?.isPaused &&
        presenceTracker?.isRunning &&
        !presenceTracker?.isPaused
    );
}

function updateTrayState() {
    if (!tray) return;

    const trackingLabel = isTrackingActive() ? 'Active' : 'Paused';
    const contextMenu = Menu.buildFromTemplate([
        {
            label: 'Open Dashboard',
            click: () => mainWindow?.show()
        },
        { type: 'separator' },
        {
            label: `Tracking Status: ${trackingLabel}`,
            enabled: false
        },
        { type: 'separator' },
        {
            label: 'Pause Tracking',
            click: () => {
                if (activityTracker) activityTracker.pause();
                if (idleDetector) idleDetector.pause();
                if (presenceTracker) presenceTracker.pause();
                updateTrayState();
            }
        },
        {
            label: 'Resume Tracking',
            click: () => {
                if (activityTracker) activityTracker.resume();
                if (idleDetector) idleDetector.resume();
                if (presenceTracker) presenceTracker.resume();
                updateTrayState();
            }
        },
        { type: 'separator' },
        {
            label: 'Quit',
            click: () => {
                app.isQuitting = true;
                app.quit();
            }
        }
    ]);

    tray.setToolTip(`Activity Tracker - ${trackingLabel}`);
    tray.setContextMenu(contextMenu);
}

function getLiveTrackingState() {
    return {
        activity: activityTracker?.getStats ? activityTracker.getStats() : null,
        idle: idleDetector?.getStats ? idleDetector.getStats() : null,
        presence: presenceTracker?.getStats ? presenceTracker.getStats() : null
    };
}

function sendTrackingUpdate() {
    if (!mainWindow || mainWindow.isDestroyed()) return;
    mainWindow.webContents.send('tracking:update', {
        sent_at: new Date().toISOString(),
        status: {
            activityTracking: !!(activityTracker?.isRunning && !activityTracker?.isPaused),
            idleTracking: !!(idleDetector?.isRunning && !idleDetector?.isPaused),
            presenceTracking: !!(presenceTracker?.isRunning && !presenceTracker?.isPaused),
            syncEnabled: dataSync?.isRunning || false
        },
        live: getLiveTrackingState()
    });
}

function startTrackingUpdateTimer() {
    if (trackingUpdateTimer) return;
    trackingUpdateTimer = setInterval(sendTrackingUpdate, 2000);
}

function stopTrackingUpdateTimer() {
    if (!trackingUpdateTimer) return;
    clearInterval(trackingUpdateTimer);
    trackingUpdateTimer = null;
}

function flushLiveTrackingNow() {
    activityTracker?.flushOpenInterval?.();
    idleDetector?.flushOpenInterval?.();
    presenceTracker?.flushOpenInterval?.();
}

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        minWidth: 900,
        minHeight: 600,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js')
        },
        icon: getWindowIcon(),
        show: false,
        frame: true,
        titleBarStyle: 'default'
    });

    // Load the app
    if (isDev) {
        mainWindow.loadURL('http://localhost:5173');
        mainWindow.webContents.openDevTools();
    } else {
        mainWindow.loadFile(path.join(__dirname, '../../dist-renderer/index.html'));
    }

    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
    });

    mainWindow.on('close', (event) => {
        if (!app.isQuitting) {
            event.preventDefault();
            mainWindow.hide();
        }
    });
}

function createTray() {
    tray = new Tray(getTrayIcon());
    updateTrayState();
    
    tray.on('click', () => {
        mainWindow?.show();
    });
}

function stopSessionServices() {
    stopTrackingUpdateTimer();
    if (activityTracker) {
        activityTracker.stop();
        activityTracker = null;
    }
    if (idleDetector) {
        idleDetector.stop();
        idleDetector = null;
    }
    if (presenceTracker) {
        presenceTracker.stop();
        presenceTracker = null;
    }
    if (dataSync) {
        dataSync.stop();
        dataSync = null;
    }
    if (browserUsageServer) {
        browserUsageServer.stop();
        browserUsageServer = null;
    }
    localStorage = null;
    updateTrayState();
}

function clearStoredSession() {
    stopSessionServices();
    store.delete('authToken');
    store.delete('refreshToken');
    store.delete('user');
    store.delete('deviceId');
    store.delete('machineId');
}

async function refreshStoredAuthToken() {
    const refreshToken = store.get('refreshToken');
    if (!refreshToken) {
        clearStoredSession();
        return null;
    }

    try {
        const response = await axios.post(apiUrl('/auth/refresh'), null, {
            params: { refresh_token: refreshToken },
        });
        const { access_token, refresh_token, user } = response.data;

        store.set('authToken', access_token);
        store.set('refreshToken', refresh_token);
        store.set('user', user);

        if (dataSync) {
            dataSync.updateToken(access_token);
        }

        return access_token;
    } catch (error) {
        clearStoredSession();
        return null;
    }
}

async function apiRequest(config, retryOnUnauthorized = true) {
    const authToken = store.get('authToken');
    const headers = { ...(config.headers || {}) };
    if (authToken) {
        headers.Authorization = `Bearer ${authToken}`;
    }

    try {
        return await axios({ ...config, headers });
    } catch (error) {
        if (retryOnUnauthorized && error.response?.status === 401) {
            const refreshedToken = await refreshStoredAuthToken();
            if (refreshedToken) {
                return axios({
                    ...config,
                    headers: {
                        ...headers,
                        Authorization: `Bearer ${refreshedToken}`,
                    },
                });
            }
        }
        throw error;
    }
}

function startSessionServices({ user, authToken }) {
    if (!user?.id || !authToken || !store.get('deviceId')) {
        return;
    }

    stopSessionServices();
    localStorage = new LocalStorage(`user-${user.id}`);
    
    activityTracker = new ActivityTracker(localStorage, {
        storeWindowTitle: store.get('storeWindowTitle', false)
    });
    activityTracker.start();
    
    idleDetector = new IdleDetector(localStorage, {
        idleThreshold: store.get('idleThreshold', 60),
        chunkFlushInterval: 10
    });
    idleDetector.start();

    presenceTracker = new PresenceTracker(localStorage, {
        statusUrl: store.get('webcamStatusUrl', 'http://127.0.0.1:8001/status'),
        pollInterval: store.get('presencePollInterval', 5000)
    });
    presenceTracker.start();

    browserUsageServer = new BrowserUsageServer(localStorage, {
        host: '127.0.0.1',
        port: 8080
    });
    browserUsageServer.start();

    dataSync = new DataSync(localStorage, authToken, {
        baseUrl: getApiBaseUrl(),
        syncInterval: getSyncIntervalMs(),
        beforeSync: flushLiveTrackingNow,
        request: (config) => apiRequest(config),
        onSyncComplete: (payload) => {
            if (mainWindow && !mainWindow.isDestroyed()) {
                mainWindow.webContents.send('sync:complete', payload);
            }
        }
    });
    dataSync.start();
    startTrackingUpdateTimer();
    sendTrackingUpdate();
    updateTrayState();
}

async function restoreSessionServices() {
    const authToken = store.get('authToken');
    const user = store.get('user');
    const deviceId = store.get('deviceId');

    if (authToken && user?.id && deviceId) {
        try {
            await apiRequest({
                method: 'get',
                url: apiUrl('/auth/me'),
            });
            startSessionServices({
                user: store.get('user'),
                authToken: store.get('authToken'),
            });
        } catch (error) {
            clearStoredSession();
        }
    }
}

// IPC Handlers
function setupIPC() {
    // Auth
    ipcMain.handle('auth:login', async (event, { email, password }) => {
        try {
            const response = await axios.post(apiUrl('/auth/login'), {
                email, password
            });
            const { access_token, refresh_token, user } = response.data;
            stopSessionServices();
            store.set('authToken', access_token);
            store.set('refreshToken', refresh_token);
            store.set('user', user);
            store.delete('deviceId');
            store.delete('machineId');
            
            return { success: true, user };
        } catch (error) {
            return { success: false, error: error.response?.data?.detail || 'Login failed' };
        }
    });

    ipcMain.handle('auth:logout', async () => {
        clearStoredSession();
        return { success: true };
    });

    ipcMain.handle('auth:getUser', () => {
        return store.get('user', null);
    });

    ipcMain.handle('auth:isLoggedIn', () => {
        return !!store.get('authToken') && !!store.get('user');
    });

    // Device registration
    ipcMain.handle('device:register', async () => {
        const { v4: uuidv4 } = require('uuid');
        const os = require('os');
        
        let machineId = store.get('machineId');
        if (!machineId) {
            machineId = uuidv4();
            store.set('machineId', machineId);
        }
        
        try {
            const response = await apiRequest({
                method: 'post',
                url: apiUrl('/devices/register'),
                data: {
                    machine_id: machineId,
                    hostname: os.hostname(),
                    os: process.platform,
                    os_version: os.release(),
                    app_version: app.getVersion()
                },
            });
            store.set('deviceId', response.data.id);
            startSessionServices({
                user: store.get('user'),
                authToken: store.get('authToken')
            });
            return { success: true, device: response.data };
        } catch (error) {
            return { success: false, error: error.response?.data?.detail || 'Registration failed' };
        }
    });

    // Tracking control
    ipcMain.handle('tracking:getStatus', () => {
        return {
            activityTracking: !!(activityTracker?.isRunning && !activityTracker?.isPaused),
            idleTracking: !!(idleDetector?.isRunning && !idleDetector?.isPaused),
            presenceTracking: !!(presenceTracker?.isRunning && !presenceTracker?.isPaused),
            syncEnabled: dataSync?.isRunning || false
        };
    });

    ipcMain.handle('tracking:pause', () => {
        if (activityTracker) activityTracker.pause();
        if (idleDetector) idleDetector.pause();
        if (presenceTracker) presenceTracker.pause();
        sendTrackingUpdate();
        updateTrayState();
        return { success: true };
    });

    ipcMain.handle('tracking:resume', () => {
        if (activityTracker) activityTracker.resume();
        if (idleDetector) idleDetector.resume();
        if (presenceTracker) presenceTracker.resume();
        sendTrackingUpdate();
        updateTrayState();
        return { success: true };
    });

    ipcMain.handle('sync:now', async () => {
        if (!dataSync) return { success: false, error: 'Sync is not initialized' };
        flushLiveTrackingNow();
        await dataSync.syncNow();
        sendTrackingUpdate();
        return { success: true };
    });

    // Reports
    ipcMain.handle('reports:getTodaySummary', async () => {
        const targetDate = getLocalDateString();
        const localSummary = buildLocalDailySummary(localStorage, targetDate, getLiveTrackingState());
        try {
            const response = await apiRequest({
                method: 'get',
                url: apiUrl(`/me/summary?target_date=${targetDate}`),
            });
            return mergeSummaries(response.data, localSummary);
        } catch (error) {
            console.error('[Reports] Summary failed:', error.response?.data || error.message);
            return localSummary;
        }
    });

    ipcMain.handle('reports:getTimeline', async (event, date) => {
        const targetDate = date || getLocalDateString();
        const localTimeline = buildLocalTimeline(localStorage, targetDate, getLiveTrackingState());
        try {
            const response = await apiRequest({
                method: 'get',
                url: apiUrl(`/me/timeline?target_date=${targetDate}`),
            });
            return mergeTimelines(response.data, localTimeline);
        } catch (error) {
            console.error('[Reports] Timeline failed:', error.response?.data || error.message);
            return localTimeline;
        }
    });

    ipcMain.handle('reports:getWeekly', async (event, weekOffset = 0) => {
        try {
            const response = await apiRequest({
                method: 'get',
                url: apiUrl(`/me/weekly?week_offset=${weekOffset}`),
            });
            return response.data;
        } catch (error) {
            console.error('[Reports] Weekly failed:', error.response?.data || error.message);
            return null;
        }
    });

    // Settings
    ipcMain.handle('settings:get', (event, key) => {
        return store.get(key);
    });

    ipcMain.handle('settings:set', (event, key, value) => {
        store.set(key, value);

        // Apply runtime settings without requiring app restart.
        if (key === 'idleThreshold' && idleDetector) {
            idleDetector.setIdleThreshold(value);
        }

        if (key === 'storeWindowTitle' && activityTracker) {
            activityTracker.setStoreWindowTitle(value);
        }

        if (key === 'syncInterval' && dataSync) {
            dataSync.setSyncInterval(getSyncIntervalMs());
        }

        return { success: true };
    });
}

// App lifecycle
app.whenReady().then(async () => {
    setupIPC();
    await restoreSessionServices();
    createWindow();
    createTray();
});

app.on('window-all-closed', () => {
    // Don't quit on macOS
    if (process.platform !== 'darwin') {
        // Keep running in background
    }
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
    } else {
        mainWindow.show();
    }
});

app.on('before-quit', () => {
    app.isQuitting = true;
    stopSessionServices();
});

// Auto-start on boot (Windows)
if (process.platform === 'win32') {
    app.setLoginItemSettings({
        openAtLogin: true,
        openAsHidden: true
    });
}
