import React, { useEffect, useState } from 'react';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [trackingStatus, setTrackingStatus] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadData();
    loadTrackingStatus();
    
    // Refresh every minute
    const interval = setInterval(loadData, 60000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const data = await window.electronAPI.getTodaySummary();
      setSummary(data);
    } catch (error) {
      console.error('Failed to load summary:', error);
    } finally {
      setIsLoading(false);
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

  const formatTime = (seconds) => {
    if (!seconds) return '0m';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  const productivityData = summary ? [
    { name: 'Productive', value: summary.productive_sec || 0, color: '#10b981' },
    { name: 'Neutral', value: summary.neutral_sec || 0, color: '#6366f1' },
    { name: 'Unproductive', value: summary.unproductive_sec || 0, color: '#f43f5e' },
  ].filter(d => d.value > 0) : [];

  const presenceData = summary ? [
    { name: 'Present', value: summary.present_sec || 0, color: '#10b981' },
    { name: 'Absent', value: summary.absent_sec || 0, color: '#f43f5e' },
    { name: 'Camera Off', value: summary.camera_off_sec || 0, color: '#6b7280' },
  ].filter(d => d.value > 0) : [];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-display font-bold text-white">Dashboard</h1>
          <p className="text-white/40 mt-1">Your activity summary for today</p>
        </div>
        <div className="flex items-center gap-2">
          <span className={trackingStatus?.activityTracking ? 'status-online' : 'status-offline'}></span>
          <span className="text-sm text-white/60">
            {trackingStatus?.activityTracking ? 'Tracking Active' : 'Tracking Paused'}
          </span>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Focus Time"
          value={formatTime(summary?.focus_sec)}
          icon="⏱️"
          gradient="from-emerald-500/20 to-teal-500/20"
          iconBg="from-emerald-500 to-teal-500"
        />
        <StatCard
          title="Idle Time"
          value={formatTime(summary?.idle_sec)}
          icon="💤"
          gradient="from-amber-500/20 to-orange-500/20"
          iconBg="from-amber-500 to-orange-500"
        />
        <StatCard
          title="Present Time"
          value={formatTime(summary?.present_sec)}
          icon="👤"
          gradient="from-blue-500/20 to-indigo-500/20"
          iconBg="from-blue-500 to-indigo-500"
        />
        <StatCard
          title="Productive"
          value={formatTime(summary?.productive_sec)}
          icon="🚀"
          gradient="from-purple-500/20 to-pink-500/20"
          iconBg="from-purple-500 to-pink-500"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Productivity Chart */}
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Productivity Breakdown</h3>
          {productivityData.length > 0 ? (
            <div className="flex items-center gap-8">
              <ResponsiveContainer width={160} height={160}>
                <PieChart>
                  <Pie
                    data={productivityData}
                    innerRadius={50}
                    outerRadius={70}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {productivityData.map((entry, index) => (
                      <Cell key={index} fill={entry.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-3">
                {productivityData.map((item, index) => (
                  <div key={index} className="flex items-center gap-3">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }}></div>
                    <span className="text-white/60">{item.name}</span>
                    <span className="text-white font-medium">{formatTime(item.value)}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-white/40 text-center py-8">No data available</p>
          )}
        </div>

        {/* Presence Chart */}
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Presence Status</h3>
          {presenceData.length > 0 ? (
            <div className="flex items-center gap-8">
              <ResponsiveContainer width={160} height={160}>
                <PieChart>
                  <Pie
                    data={presenceData}
                    innerRadius={50}
                    outerRadius={70}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {presenceData.map((entry, index) => (
                      <Cell key={index} fill={entry.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-3">
                {presenceData.map((item, index) => (
                  <div key={index} className="flex items-center gap-3">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }}></div>
                    <span className="text-white/60">{item.name}</span>
                    <span className="text-white font-medium">{formatTime(item.value)}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-white/40 text-center py-8">No presence data</p>
          )}
        </div>
      </div>

      {/* Top Apps and Domains */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Apps */}
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Top Applications</h3>
          {summary?.top_apps?.length > 0 ? (
            <div className="space-y-3">
              {summary.top_apps.slice(0, 5).map((app, index) => (
                <div key={index} className="flex items-center gap-4">
                  <span className="text-2xl">
                    {getAppIcon(app.app_name)}
                  </span>
                  <div className="flex-1">
                    <p className="text-white font-medium">{app.app_name}</p>
                    <div className="mt-1 h-2 bg-white/10 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-primary-500 to-accent-500 rounded-full"
                        style={{ width: `${(app.duration_sec / summary.focus_sec) * 100}%` }}
                      ></div>
                    </div>
                  </div>
                  <span className="text-white/60 text-sm">{formatTime(app.duration_sec)}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-white/40 text-center py-8">No app usage data</p>
          )}
        </div>

        {/* Top Domains */}
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Top Websites</h3>
          {summary?.top_domains?.length > 0 ? (
            <div className="space-y-3">
              {summary.top_domains.slice(0, 5).map((domain, index) => (
                <div key={index} className="flex items-center gap-4">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    domain.label === 'productive' ? 'bg-emerald-500/20 text-emerald-400' :
                    domain.label === 'unproductive' ? 'bg-rose-500/20 text-rose-400' :
                    'bg-gray-500/20 text-gray-400'
                  }`}>
                    {domain.label}
                  </span>
                  <div className="flex-1">
                    <p className="text-white font-medium">{domain.domain}</p>
                  </div>
                  <span className="text-white/60 text-sm">{formatTime(domain.duration_sec)}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-white/40 text-center py-8">No browser data</p>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({ title, value, icon, gradient, iconBg }) {
  return (
    <div className={`card p-6 bg-gradient-to-br ${gradient}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-white/60 text-sm">{title}</p>
          <p className="text-3xl font-bold text-white mt-2">{value}</p>
        </div>
        <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${iconBg} flex items-center justify-center text-2xl`}>
          {icon}
        </div>
      </div>
    </div>
  );
}

function getAppIcon(appName) {
  const name = appName.toLowerCase();
  if (name.includes('code') || name.includes('visual studio')) return '💻';
  if (name.includes('chrome') || name.includes('browser')) return '🌐';
  if (name.includes('slack') || name.includes('teams')) return '💬';
  if (name.includes('terminal') || name.includes('iterm')) return '⌨️';
  if (name.includes('figma') || name.includes('sketch')) return '🎨';
  if (name.includes('notion') || name.includes('notes')) return '📝';
  return '📱';
}

export default Dashboard;
