/**
 * Popup Script
 * Displays tracking status and controls
 */

const trackingStatus = document.getElementById('tracking-status');
const currentDomain = document.getElementById('current-domain');
const bufferSize = document.getElementById('buffer-size');
const toggleBtn = document.getElementById('toggle-btn');

function updateUI(status) {
    // Update tracking status
    const indicator = trackingStatus.querySelector('.indicator');
    const statusText = trackingStatus.querySelector('span:last-child');
    
    if (status.isTracking) {
        indicator.className = 'indicator active';
        statusText.textContent = 'Active';
        statusText.className = 'status-active';
        toggleBtn.textContent = 'Pause Tracking';
        toggleBtn.className = 'toggle-btn pause';
    } else {
        indicator.className = 'indicator inactive';
        statusText.textContent = 'Paused';
        statusText.className = 'status-inactive';
        toggleBtn.textContent = 'Resume Tracking';
        toggleBtn.className = 'toggle-btn resume';
    }
    
    // Update current domain
    currentDomain.textContent = status.currentDomain || '—';
    
    // Update buffer size
    bufferSize.textContent = status.bufferSize;
}

// Get initial status
chrome.runtime.sendMessage({ action: 'getStatus' }, (response) => {
    if (response) {
        updateUI(response);
    }
});

// Toggle tracking
toggleBtn.addEventListener('click', () => {
    chrome.runtime.sendMessage({ action: 'toggleTracking' }, (response) => {
        if (response) {
            updateUI({ 
                isTracking: response.isTracking,
                currentDomain: null,
                bufferSize: 0
            });
            
            // Refresh full status
            setTimeout(() => {
                chrome.runtime.sendMessage({ action: 'getStatus' }, (status) => {
                    if (status) {
                        updateUI(status);
                    }
                });
            }, 100);
        }
    });
});
