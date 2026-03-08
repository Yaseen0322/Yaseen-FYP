import React, { useEffect, useState } from 'react';

function Settings() {
  const [trackingStatus, setTrackingStatus] = useState(null);
  const [settings, setSettings] = useState({
    idleThreshold: 120,
    storeWindowTitle: false,
    syncInterval: 60
  });

  useEffect(() => {
    loadSettings();
    loadTrackingStatus();
  }, []);

  const loadSettings = async () => {
    try {
      const idleThreshold = await window.electronAPI.getSetting('idleThreshold') || 120;
      const storeWindowTitle = await window.electronAPI.getSetting('storeWindowTitle') || false;
      const rawSyncInterval = await window.electronAPI.getSetting('syncInterval');
      const syncInterval = rawSyncInterval
        ? (rawSyncInterval > 1000 ? Math.floor(rawSyncInterval / 1000) : rawSyncInterval)
        : 60;
      setSettings({ idleThreshold, storeWindowTitle, syncInterval });
    } catch (error) {
      console.error('Failed to load settings:', error);
    }
  };

  const loadTrackingStatus = async () => {
    try {
      const status = await window.electronAPI.getTrackingStatus();
      setTrackingStatus(status);
    } catch (error) {
      console.error('Failed to load tracking status:', error);
    }
  };

  const handleSettingChange = async (key, value) => {
    try {
      await window.electronAPI.setSetting(key, value);
      setSettings({ ...settings, [key]: value });
      if (key === 'idleThreshold' || key === 'syncInterval') {
        await loadTrackingStatus();
      }
    } catch (error) {
      console.error('Failed to save setting:', error);
    }
  };

  const handlePauseTracking = async () => {
    try {
      await window.electronAPI.pauseTracking();
      loadTrackingStatus();
    } catch (error) {
      console.error('Failed to pause tracking:', error);
    }
  };

  const handleResumeTracking = async () => {
    try {
      await window.electronAPI.resumeTracking();
      loadTrackingStatus();
    } catch (error) {
      console.error('Failed to resume tracking:', error);
    }
  };

  return (
    <div className="space-y-8 animate-fade-in max-w-2xl">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-display font-bold text-white">Settings</h1>
        <p className="text-white/40 mt-1">Configure your activity tracking preferences</p>
      </div>

      {/* Tracking Control */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Tracking Control</h3>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-white">Activity Tracking</p>
            <p className="text-sm text-white/40">
              {trackingStatus?.activityTracking ? 'Currently tracking your activity' : 'Tracking is paused'}
            </p>
          </div>
          {trackingStatus?.activityTracking ? (
            <button
              onClick={handlePauseTracking}
              className="px-4 py-2 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/30 text-amber-400 transition-colors"
            >
              Pause Tracking
            </button>
          ) : (
            <button
              onClick={handleResumeTracking}
              className="px-4 py-2 rounded-xl bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/30 text-emerald-400 transition-colors"
            >
              Resume Tracking
            </button>
          )}
        </div>
      </div>

      {/* Idle Detection */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Idle Detection</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-white mb-2">Idle Threshold (seconds)</label>
            <input
              type="number"
              value={settings.idleThreshold}
              onChange={(e) => {
                const value = parseInt(e.target.value, 10);
                if (Number.isFinite(value)) {
                  handleSettingChange('idleThreshold', value);
                }
              }}
              min={30}
              max={600}
              className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white focus:outline-none focus:border-primary-500"
            />
            <p className="text-sm text-white/40 mt-2">
              You'll be marked as idle after {settings.idleThreshold} seconds of inactivity
            </p>
          </div>
        </div>
      </div>

      {/* Privacy */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Privacy</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-white">Store Window Titles</p>
              <p className="text-sm text-white/40">
                Enable to track window titles (more detailed reports but less privacy)
              </p>
            </div>
            <button
              onClick={() => handleSettingChange('storeWindowTitle', !settings.storeWindowTitle)}
              className={`w-14 h-8 rounded-full transition-colors relative ${
                settings.storeWindowTitle ? 'bg-primary-500' : 'bg-white/20'
              }`}
            >
              <div
                className={`absolute top-1 w-6 h-6 bg-white rounded-full transition-transform ${
                  settings.storeWindowTitle ? 'translate-x-7' : 'translate-x-1'
                }`}
              ></div>
            </button>
          </div>
        </div>
      </div>

      {/* Sync Settings */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Sync Settings</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-white mb-2">Sync Interval (seconds)</label>
            <select
              value={settings.syncInterval}
              onChange={(e) => {
                const value = parseInt(e.target.value, 10);
                if (Number.isFinite(value)) {
                  handleSettingChange('syncInterval', value);
                }
              }}
              className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white focus:outline-none focus:border-primary-500"
            >
              <option value={30}>Every 30 seconds</option>
              <option value={60}>Every minute</option>
              <option value={300}>Every 5 minutes</option>
              <option value={600}>Every 10 minutes</option>
            </select>
            <p className="text-sm text-white/40 mt-2">
              How often to sync data with the server
            </p>
          </div>
        </div>
      </div>

      {/* Status */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-white mb-4">System Status</h3>
        <div className="space-y-3">
          <StatusRow
            label="Activity Tracking"
            status={trackingStatus?.activityTracking}
          />
          <StatusRow
            label="Idle Detection"
            status={trackingStatus?.idleTracking}
          />
          <StatusRow
            label="Server Sync"
            status={trackingStatus?.syncEnabled}
          />
        </div>
      </div>
    </div>
  );
}

function StatusRow({ label, status }) {
  return (
    <div className="flex items-center justify-between py-2">
      <span className="text-white/60">{label}</span>
      <div className="flex items-center gap-2">
        <span className={status ? 'status-online' : 'status-offline'}></span>
        <span className={status ? 'text-emerald-400' : 'text-rose-400'}>
          {status ? 'Active' : 'Inactive'}
        </span>
      </div>
    </div>
  );
}

export default Settings;
