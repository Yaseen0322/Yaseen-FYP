import React, { useEffect, useState } from 'react';

function getLocalDateString(date = new Date()) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function Timeline() {
  const [selectedDate, setSelectedDate] = useState(getLocalDateString());
  const [timeline, setTimeline] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);

  useEffect(() => {
    loadTimeline();
  }, [selectedDate]);

  useEffect(() => {
    const isToday = selectedDate === getLocalDateString();
    if (!isToday) return undefined;

    const interval = setInterval(() => loadTimeline(false), 3000);
    const unsubscribeTracking = window.electronAPI.onTrackingUpdate(() => loadTimeline(false));
    const unsubscribe = window.electronAPI.onSyncComplete(() => loadTimeline(false));
    return () => {
      clearInterval(interval);
      if (typeof unsubscribeTracking === 'function') unsubscribeTracking();
      if (typeof unsubscribe === 'function') unsubscribe();
    };
  }, [selectedDate]);

  const loadTimeline = async (initial = true) => {
    if (initial) setIsLoading(true);
    try {
      const data = await window.electronAPI.getTimeline(selectedDate);
      setTimeline(data);
      setLastUpdated(new Date());
    } catch (error) {
      console.error('Failed to load timeline:', error);
    } finally {
      if (initial) setIsLoading(false);
    }
  };

  const formatTime = (isoString) => {
    return new Date(isoString).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    });
  };

  const formatDuration = (seconds) => {
    if (!seconds || seconds < 0) return '0m';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours === 0 && minutes === 0 && seconds > 0) return '<1m';
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  const getBlockStyle = (type) => {
    switch (type) {
      case 'present':
        return 'bg-emerald-500/20 border-emerald-500/50 text-emerald-400';
      case 'absent':
        return 'bg-rose-500/20 border-rose-500/50 text-rose-400';
      case 'idle':
        return 'bg-amber-500/20 border-amber-500/50 text-amber-400';
      case 'camera_off':
        return 'bg-gray-500/20 border-gray-500/50 text-gray-400';
      case 'app_usage':
        return 'bg-blue-500/20 border-blue-500/50 text-blue-400';
      case 'browser_usage':
        return 'bg-cyan-500/20 border-cyan-500/50 text-cyan-400';
      default:
        return 'bg-white/5 border-white/20 text-white/60';
    }
  };

  const getBlockIcon = (type) => {
    switch (type) {
      case 'present': return '👤';
      case 'absent': return '🚫';
      case 'idle': return '💤';
      case 'camera_off': return '📷';
      case 'app_usage': return '💻';
      case 'browser_usage': return '🌐';
      default: return '•';
    }
  };

  const getBlockLabel = (type) => {
    switch (type) {
      case 'present': return 'Present';
      case 'absent': return 'Absent';
      case 'idle': return 'Idle';
      case 'camera_off': return 'Camera Off';
      case 'app_usage': return 'Active';
      case 'browser_usage': return 'Website';
      default: return type;
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-display font-bold text-white">Timeline</h1>
          <p className="text-white/40 mt-1">Your activity timeline for the day</p>
          {lastUpdated && (
            <p className="text-white/30 text-xs mt-1">
              Updated: {lastUpdated.toLocaleTimeString()}
            </p>
          )}
        </div>
        <input
          type="date"
          value={selectedDate}
          onChange={(e) => setSelectedDate(e.target.value)}
          className="px-4 py-2 rounded-xl bg-white/5 border border-white/10 text-white focus:outline-none focus:border-primary-500"
        />
      </div>

      {/* Timeline Legend */}
      <div className="flex flex-wrap gap-4">
        {['present', 'absent', 'idle', 'camera_off', 'app_usage', 'browser_usage'].map((type) => (
          <div key={type} className="flex items-center gap-2">
            <span className={`w-3 h-3 rounded-full ${getBlockStyle(type).replace('bg-', 'bg-').split(' ')[0].replace('/20', '')}`}></span>
            <span className="text-sm text-white/60">{getBlockLabel(type)}</span>
          </div>
        ))}
      </div>

      {/* Timeline Content */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : timeline?.blocks?.length > 0 ? (
        <div className="card p-6">
          <div className="space-y-3">
            {timeline.blocks.map((block, index) => (
              <div
                key={index}
                className={`flex items-center gap-4 p-4 rounded-xl border ${getBlockStyle(block.type)}`}
                style={{
                  animationDelay: `${index * 0.05}s`
                }}
              >
                <span className="text-2xl">{getBlockIcon(block.type)}</span>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{getBlockLabel(block.type)}</span>
                    {block.details?.app_name && (
                      <span className="text-sm opacity-70">• {block.details.app_name}</span>
                    )}
                    {block.details?.domain && (
                      <span className="text-sm opacity-70">
                        • {block.details.domain}
                        {block.details.label ? ` (${block.details.label})` : ''}
                      </span>
                    )}
                  </div>
                  <p className="text-sm opacity-60 mt-1">
                    {formatTime(block.start_ts)} - {formatTime(block.end_ts)}
                  </p>
                </div>
                <span className="text-sm font-medium">
                  {formatDuration(block.duration_sec)}
                </span>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="card p-12 text-center">
          <span className="text-6xl">📅</span>
          <p className="text-white/60 mt-4">No activity recorded for this date</p>
        </div>
      )}
    </div>
  );
}

export default Timeline;
