/**
 * Background Service Worker
 * Tracks active tab domains and sends to local agent
 * Privacy: Only domain names tracked, no page content
 */

// Configuration
const CONFIG = {
    agentUrl: 'http://localhost:8080/browser-usage',
    sendInterval: 30000, // 30 seconds
    minDuration: 5, // Minimum seconds to track
};

// State
let currentTabInfo = null;
let usageBuffer = [];
let isTracking = true;

// Extract domain from URL
function extractDomain(url) {
    try {
        const urlObj = new URL(url);
        return urlObj.hostname;
    } catch {
        return null;
    }
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
    if (!tab || !tab.url || tab.url.startsWith('chrome://') || tab.url.startsWith('about:')) {
        currentTabInfo = null;
        return;
    }

    const domain = extractDomain(tab.url);
    if (!domain) {
        currentTabInfo = null;
        return;
    }

    // Save previous tab usage if exists
    if (currentTabInfo && currentTabInfo.domain !== domain) {
        finalizeCurrentTab();
    }

    currentTabInfo = {
        domain: domain,
        browser: getBrowserName(),
        startTime: new Date(),
    };
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
}

// Send buffered data to agent
async function sendToAgent() {
    if (usageBuffer.length === 0) return;

    const dataToSend = [...usageBuffer];
    usageBuffer = [];

    try {
        const response = await fetch(CONFIG.agentUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ items: dataToSend }),
        });

        if (!response.ok) {
            // Put data back in buffer if failed
            usageBuffer = [...dataToSend, ...usageBuffer];
            console.error('Failed to send browser usage:', response.status);
        } else {
            console.log(`Sent ${dataToSend.length} browser usage records`);
        }
    } catch (error) {
        // Put data back in buffer if failed
        usageBuffer = [...dataToSend, ...usageBuffer];
        console.error('Error sending browser usage:', error);
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

// Periodic send
setInterval(() => {
    if (isTracking) {
        // Finalize and restart current tab to get accurate timing
        if (currentTabInfo) {
            const domain = currentTabInfo.domain;
            const browser = currentTabInfo.browser;
            finalizeCurrentTab();
            currentTabInfo = {
                domain: domain,
                browser: browser,
                startTime: new Date(),
            };
        }
        sendToAgent();
    }
}, CONFIG.sendInterval);

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
        sendResponse({ isTracking: isTracking });
    }
    return true;
});

// Initial tab tracking
chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs[0]) {
        startTracking(tabs[0]);
    }
});

console.log('Activity Tracker Browser Extension loaded');
