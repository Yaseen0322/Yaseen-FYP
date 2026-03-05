/**
 * Electron Main Process
 * Handles: window management, system tray, activity tracking, IPC
 */
const { app, BrowserWindow, Tray, Menu, ipcMain, nativeImage } = require('electron');
const path = require('path');
const { ActivityTracker } = require('./modules/activity-tracker');
const { IdleDetector } = require('./modules/idle-detector');
const { PresenceTracker } = require('./modules/presence-tracker');
const { DataSync } = require('./modules/data-sync');
const { BrowserUsageServer } = require('./modules/browser-usage-server');
const { LocalStorage } = require('./modules/local-storage');
const Store = require('electron-store');

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

const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;

function getApiBaseUrl() {
    return store.get('apiBaseUrl', DEFAULT_API_BASE_URL);
}

function apiUrl(path) {
    return `${getApiBaseUrl()}${path}`;
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
        icon: path.join(__dirname, '../../assets/icon.png'),
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
    const iconPath = path.join(__dirname, '../../assets/tray-icon.png');
    tray = new Tray(nativeImage.createEmpty());
    
    const contextMenu = Menu.buildFromTemplate([
        { 
            label: 'Open Dashboard', 
            click: () => mainWindow.show() 
        },
        { type: 'separator' },
        { 
            label: 'Tracking Status',
            sublabel: 'Active',
            enabled: false
        },
        { type: 'separator' },
        { 
            label: 'Pause Tracking', 
            click: () => {
                if (activityTracker) activityTracker.pause();
                if (idleDetector) idleDetector.pause();
                if (presenceTracker) presenceTracker.pause();
            }
        },
        { 
            label: 'Resume Tracking', 
            click: () => {
                if (activityTracker) activityTracker.resume();
                if (idleDetector) idleDetector.resume();
                if (presenceTracker) presenceTracker.resume();
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

    tray.setToolTip('Activity Tracker - Running');
    tray.setContextMenu(contextMenu);
    
    tray.on('click', () => {
        mainWindow.show();
    });
}

function initializeTracking() {
    // Initialize local storage
    localStorage = new LocalStorage();
    
    // Initialize activity tracker
    activityTracker = new ActivityTracker(localStorage);
    activityTracker.start();
    
    // Initialize idle detector
    idleDetector = new IdleDetector(localStorage, {
        idleThreshold: store.get('idleThreshold', 120) // 2 minutes
    });
    idleDetector.start();

    // Initialize presence tracker (poll webcam-service)
    presenceTracker = new PresenceTracker(localStorage, {
        statusUrl: store.get('webcamStatusUrl', 'http://127.0.0.1:8001/status'),
        pollInterval: store.get('presencePollInterval', 10000)
    });
    presenceTracker.start();

    // Receive browser usage from extension on localhost:8080
    browserUsageServer = new BrowserUsageServer(localStorage, {
        host: '127.0.0.1',
        port: 8080
    });
    browserUsageServer.start();
    
    // Initialize data sync
    const authToken = store.get('authToken');
    if (authToken) {
        dataSync = new DataSync(localStorage, authToken, {
            baseUrl: getApiBaseUrl(),
            syncInterval: store.get('syncInterval', 60000)
        });
        dataSync.start();
    }
}

// IPC Handlers
function setupIPC() {
    // Auth
    ipcMain.handle('auth:login', async (event, { email, password }) => {
        const axios = require('axios');
        try {
            const response = await axios.post(apiUrl('/auth/login'), {
                email, password
            });
            const { access_token, refresh_token, user } = response.data;
            store.set('authToken', access_token);
            store.set('refreshToken', refresh_token);
            store.set('user', user);
            
            // Start data sync
            if (dataSync) dataSync.stop();
            dataSync = new DataSync(localStorage, access_token, {
                baseUrl: getApiBaseUrl(),
                syncInterval: store.get('syncInterval', 60000)
            });
            dataSync.start();
            
            return { success: true, user };
        } catch (error) {
            return { success: false, error: error.response?.data?.detail || 'Login failed' };
        }
    });

    ipcMain.handle('auth:logout', async () => {
        store.delete('authToken');
        store.delete('refreshToken');
        store.delete('user');
        if (dataSync) dataSync.stop();
        return { success: true };
    });

    ipcMain.handle('auth:getUser', () => {
        return store.get('user', null);
    });

    ipcMain.handle('auth:isLoggedIn', () => {
        return !!store.get('authToken');
    });

    // Device registration
    ipcMain.handle('device:register', async () => {
        const axios = require('axios');
        const { v4: uuidv4 } = require('uuid');
        const os = require('os');
        
        let machineId = store.get('machineId');
        if (!machineId) {
            machineId = uuidv4();
            store.set('machineId', machineId);
        }
        
        try {
            const response = await axios.post(
                apiUrl('/devices/register'),
                {
                    machine_id: machineId,
                    hostname: os.hostname(),
                    os: process.platform,
                    os_version: os.release(),
                    app_version: app.getVersion()
                },
                {
                    headers: { Authorization: `Bearer ${store.get('authToken')}` }
                }
            );
            store.set('deviceId', response.data.id);
            return { success: true, device: response.data };
        } catch (error) {
            return { success: false, error: error.response?.data?.detail || 'Registration failed' };
        }
    });

    // Tracking control
    ipcMain.handle('tracking:getStatus', () => {
        return {
            activityTracking: activityTracker?.isRunning || false,
            idleTracking: idleDetector?.isRunning || false,
            presenceTracking: presenceTracker?.isRunning || false,
            syncEnabled: dataSync?.isRunning || false
        };
    });

    ipcMain.handle('tracking:pause', () => {
        if (activityTracker) activityTracker.pause();
        if (idleDetector) idleDetector.pause();
        if (presenceTracker) presenceTracker.pause();
        return { success: true };
    });

    ipcMain.handle('tracking:resume', () => {
        if (activityTracker) activityTracker.resume();
        if (idleDetector) idleDetector.resume();
        if (presenceTracker) presenceTracker.resume();
        return { success: true };
    });

    // Reports
    ipcMain.handle('reports:getTodaySummary', async () => {
        const axios = require('axios');
        try {
            const response = await axios.get(
                apiUrl('/me/summary'),
                {
                    headers: { Authorization: `Bearer ${store.get('authToken')}` }
                }
            );
            return response.data;
        } catch (error) {
            console.error('[Reports] Summary failed:', error.response?.data || error.message);
            return null;
        }
    });

    ipcMain.handle('reports:getTimeline', async (event, date) => {
        const axios = require('axios');
        try {
            const response = await axios.get(
                apiUrl(`/me/timeline?target_date=${date}`),
                {
                    headers: { Authorization: `Bearer ${store.get('authToken')}` }
                }
            );
            return response.data;
        } catch (error) {
            console.error('[Reports] Timeline failed:', error.response?.data || error.message);
            return null;
        }
    });

    ipcMain.handle('reports:getWeekly', async (event, weekOffset = 0) => {
        const axios = require('axios');
        try {
            const response = await axios.get(
                apiUrl(`/me/weekly?week_offset=${weekOffset}`),
                {
                    headers: { Authorization: `Bearer ${store.get('authToken')}` }
                }
            );
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
        return { success: true };
    });
}

// App lifecycle
app.whenReady().then(() => {
    createWindow();
    createTray();
    setupIPC();
    initializeTracking();
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
    if (activityTracker) activityTracker.stop();
    if (idleDetector) idleDetector.stop();
    if (presenceTracker) presenceTracker.stop();
    if (dataSync) dataSync.stop();
    if (browserUsageServer) browserUsageServer.stop();
});

// Auto-start on boot (Windows)
if (process.platform === 'win32') {
    app.setLoginItemSettings({
        openAtLogin: true,
        openAsHidden: true
    });
}
