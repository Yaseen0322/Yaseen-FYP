/**
 * Background Service Worker
 * Tracks active tab domains and sends to local agent
 * Privacy: Only domain names tracked, no page content
 */

// Configuration
const CONFIG = {
    agentUrl: 'http://127.0.0.1:8080/browser-usage',
    sendInterval: 5000, // 5 seconds for near-real-time dashboard updates
    minDuration: 2, // Minimum seconds to track
    alarmName: 'flush-browser-usage',
};

// State
let currentTabInfo = null;
let usageBuffer = [];
let isTracking = true;
let isSending = false;
let lastPersistedAt = 0;

function isTrackableUrl(url) {
    return !!(
        url &&
        !url.startsWith('chrome://') &&
        !url.startsWith('about:') &&
        !url.startsWith('edge://') &&
        !url.startsWith('brave://') &&
        !url.startsWith('chrome-extension://') &&
        !url.startsWith('moz-extension://')
    );
}

// Extract domain from URL
function extractDomain(url) {
    try {
        const urlObj = new URL(url);
        return normalizeDomain(urlObj.hostname);
    } catch {
        return null;
    }
}

function normalizeDomain(hostname) {
    const domain = String(hostname || '')
        .trim()
        .toLowerCase()
        .replace(/^\.+|\.+$/g, '')
        .replace(/^www\./, '');

    if (!domain || domain === 'localhost' || !domain.includes('.')) {
        return null;
    }

    return domain;
}

// Get browser name
function getBrowserName() {
    const userAgent = navigator.userAgent;
    if (userAgent.includes('Chrome')) return 'Chrome';
    if (userAgent.includes('Firefox')) return 'Firefox';
    if (userAgent.includes('Edge')) return 'Edge';
    if (userAgent.includes('Safari')) return 'Safari';
    return 'Unknown';
}

// Start tracking a new tab
function startTracking(tab) {
    if (!tab || !isTrackableUrl(tab.url)) {
        finalizeCurrentTab();
        return;
    }

    const domain = extractDomain(tab.url);
    if (!domain) {
        finalizeCurrentTab();
        return;
    }

    const nextTabId = tab.id ?? null;
    const nextWindowId = tab.windowId ?? null;

    if (
        currentTabInfo &&
        currentTabInfo.domain === domain &&
        currentTabInfo.tabId === nextTabId &&
        currentTabInfo.windowId === nextWindowId
    ) {
        return;
    }

    finalizeCurrentTab();

    currentTabInfo = {
        domain: domain,
        browser: getBrowserName(),
        tabId: nextTabId,
        windowId: nextWindowId,
        startTime: new Date(),
    };
    persistState();
}

// Finalize current tab tracking
function finalizeCurrentTab() {
    if (!currentTabInfo) return;

    const endTime = new Date();
    const durationMs = endTime - currentTabInfo.startTime;
    const durationSec = Math.floor(durationMs / 1000);

    if (durationSec >= CONFIG.minDuration) {
        usageBuffer.push({
            browser: currentTabInfo.browser,
            domain: currentTabInfo.domain,
            start_ts: currentTabInfo.startTime.toISOString(),
            end_ts: endTime.toISOString(),
            duration_sec: durationSec,
        });
    }

    currentTabInfo = null;
    persistState();
}

// Send buffered data to agent
async function sendToAgent() {
    if (isSending || usageBuffer.length === 0) return;
    isSending = true;

    const dataToSend = [...usageBuffer];
    usageBuffer = [];
    persistState();

    try {
        const response = await fetch(CONFIG.agentUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ items: dataToSend }),
            keepalive: true
        });

        if (!response.ok) {
            // Put data back in buffer if failed
            usageBuffer = [...dataToSend, ...usageBuffer];
            persistState();
            console.error('Failed to send browser usage:', response.status);
        } else {
            console.log(`Sent ${dataToSend.length} browser usage records`);
            persistState();
        }
    } catch (error) {
        // Put data back in buffer if failed
        usageBuffer = [...dataToSend, ...usageBuffer];
        persistState();
        console.error('Error sending browser usage:', error);
    } finally {
        isSending = false;
    }
}

// Listen for tab activation
chrome.tabs.onActivated.addListener(async (activeInfo) => {
    if (!isTracking) return;

    try {
        const tab = await chrome.tabs.get(activeInfo.tabId);
        startTracking(tab);
    } catch (error) {
        console.error('Error getting tab info:', error);
    }
});

// Listen for tab URL changes
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (!isTracking) return;
    
    if (changeInfo.url) {
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            if (tabs[0] && tabs[0].id === tabId) {
                startTracking(tab);
            }
        });
    }
});

// Listen for window focus changes
chrome.windows.onFocusChanged.addListener(async (windowId) => {
    if (!isTracking) return;

    if (windowId === chrome.windows.WINDOW_ID_NONE) {
        finalizeCurrentTab();
    } else {
        try {
            const tabs = await chrome.tabs.query({ active: true, windowId });
            if (tabs[0]) {
                startTracking(tabs[0]);
            }
        } catch (error) {
            console.error('Error on window focus change:', error);
        }
    }
});

async function refreshActiveTabTracking() {
    if (currentTabInfo) return;

    try {
        const tabs = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
        if (tabs[0]) {
            startTracking(tabs[0]);
        }
    } catch (error) {
        console.error('Error refreshing active tab tracking:', error);
    }
}

async function flushTick() {
    if (!isTracking) return;

    await refreshActiveTabTracking();

    // Finalize and restart current tab to get accurate timing.
    if (currentTabInfo) {
        const domain = currentTabInfo.domain;
        const browser = currentTabInfo.browser;
        const tabId = currentTabInfo.tabId ?? null;
        const windowId = currentTabInfo.windowId ?? null;
        finalizeCurrentTab();
        currentTabInfo = {
            domain: domain,
            browser: browser,
            tabId: tabId,
            windowId: windowId,
            startTime: new Date(),
        };
    }

    await sendToAgent();
}

function persistState(force = false) {
    const now = Date.now();
    if (!force && now - lastPersistedAt < 3000) return;
    lastPersistedAt = now;
    chrome.storage.local.set({
        usageBuffer,
        currentTabInfo: currentTabInfo
            ? { ...currentTabInfo, startTime: currentTabInfo.startTime.toISOString() }
            : null,
        isTracking
    });
}

async function restoreState() {
    try {
        const data = await chrome.storage.local.get(['usageBuffer', 'currentTabInfo', 'isTracking']);
        usageBuffer = Array.isArray(data.usageBuffer) ? data.usageBuffer : [];
        if (typeof data.isTracking === 'boolean') {
            isTracking = data.isTracking;
        }
        if (data.currentTabInfo?.domain && data.currentTabInfo?.startTime) {
            currentTabInfo = {
                ...data.currentTabInfo,
                startTime: new Date(data.currentTabInfo.startTime)
            };
        }
    } catch (error) {
        console.error('Failed to restore extension state:', error);
    }
}

// Handle messages from popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === 'getStatus') {
        sendResponse({
            isTracking: isTracking,
            currentDomain: currentTabInfo?.domain || null,
            bufferSize: usageBuffer.length,
        });
    } else if (message.action === 'toggleTracking') {
        isTracking = !isTracking;
        if (!isTracking) {
            finalizeCurrentTab();
        }
        persistState(true);
        sendResponse({ isTracking: isTracking });
    }
    return true;
});

chrome.runtime.onSuspend.addListener(() => {
    finalizeCurrentTab();
    persistState(true);
});

chrome.alarms.onAlarm.addListener((alarm) => {
    if (alarm.name === CONFIG.alarmName) {
        flushTick();
    }
});

setInterval(flushTick, CONFIG.sendInterval);

async function initialize() {
    await restoreState();
    chrome.alarms.clear(CONFIG.alarmName, () => {
        chrome.alarms.create(CONFIG.alarmName, {
            periodInMinutes: Math.max(CONFIG.sendInterval / 60000, 0.5)
        });
    });

    chrome.tabs.query({ active: true, lastFocusedWindow: true }, (tabs) => {
        if (tabs[0]) {
            startTracking(tabs[0]);
        }
    });
}

initialize();

console.log('Activity Tracker Browser Extension loaded');
