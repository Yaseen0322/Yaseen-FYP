import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import api from '../utils/api';

function EmployeeDetail() {
  const { id } = useParams();
  const [summary, setSummary] = useState(null);
  const [timeline, setTimeline] = useState(null);
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, [id, selectedDate]);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [summaryRes, timelineRes] = await Promise.all([
        api.get(`/manager/employees/${id}/summary?target_date=${selectedDate}`),
        api.get(`/manager/employees/${id}/timeline?target_date=${selectedDate}`)
      ]);
      setSummary(summaryRes.data);
      setTimeline(timelineRes.data);
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setIsLoading(false);
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
        <div className="w-10 h-10 border-4 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            to="/employees"
            className="p-2 rounded-lg hover:bg-slate-100 transition-colors"
          >
            ← Back
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-slate-800">{summary?.employee?.name}</h1>
            <p className="text-slate-500">{summary?.employee?.email}</p>
          </div>
        </div>
        <input
          type="date"
          value={selectedDate}
          onChange={(e) => setSelectedDate(e.target.value)}
          className="px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
        />
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard title="Focus Time" value={formatTime(summary?.focus_sec)} color="text-emerald-600" />
        <StatCard title="Idle Time" value={formatTime(summary?.idle_sec)} color="text-amber-600" />
        <StatCard title="Present Time" value={formatTime(summary?.present_sec)} color="text-blue-600" />
        <StatCard title="Productive Time" value={formatTime(summary?.productive_sec)} color="text-purple-600" />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Productivity */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-lg font-semibold text-slate-800 mb-4">Productivity</h3>
          {productivityData.length > 0 ? (
            <div className="flex items-center gap-8">
              <ResponsiveContainer width={140} height={140}>
                <PieChart>
                  <Pie
                    data={productivityData}
                    innerRadius={45}
                    outerRadius={60}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {productivityData.map((entry, index) => (
                      <Cell key={index} fill={entry.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-2">
                {productivityData.map((item, index) => (
                  <div key={index} className="flex items-center gap-3">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }}></div>
                    <span className="text-slate-600">{item.name}</span>
                    <span className="font-medium text-slate-800">{formatTime(item.value)}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-slate-400 text-center py-8">No data</p>
          )}
        </div>

        {/* Presence */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-lg font-semibold text-slate-800 mb-4">Presence</h3>
          {presenceData.length > 0 ? (
            <div className="flex items-center gap-8">
              <ResponsiveContainer width={140} height={140}>
                <PieChart>
                  <Pie
                    data={presenceData}
                    innerRadius={45}
                    outerRadius={60}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {presenceData.map((entry, index) => (
                      <Cell key={index} fill={entry.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-2">
                {presenceData.map((item, index) => (
                  <div key={index} className="flex items-center gap-3">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }}></div>
                    <span className="text-slate-600">{item.name}</span>
                    <span className="font-medium text-slate-800">{formatTime(item.value)}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-slate-400 text-center py-8">No data</p>
          )}
        </div>
      </div>

      {/* Top Apps */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <h3 className="text-lg font-semibold text-slate-800 mb-4">Top Applications</h3>
        {summary?.top_apps?.length > 0 ? (
          <div className="space-y-3">
            {summary.top_apps.map((app, index) => (
              <div key={index} className="flex items-center gap-4">
                <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center text-lg">
                  💻
                </div>
                <div className="flex-1">
                  <p className="font-medium text-slate-800">{app.app_name}</p>
                  <div className="mt-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary-500 rounded-full"
                      style={{ width: `${(app.duration_sec / summary.focus_sec) * 100}%` }}
                    ></div>
                  </div>
                </div>
                <span className="text-sm text-slate-600">{formatTime(app.duration_sec)}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-slate-400 text-center py-8">No app usage data</p>
        )}
      </div>

      {/* Top Domains */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <h3 className="text-lg font-semibold text-slate-800 mb-4">Top Websites</h3>
        {summary?.top_domains?.length > 0 ? (
          <div className="space-y-3">
            {summary.top_domains.map((domain, index) => (
              <div key={index} className="flex items-center gap-4">
                <span className={`px-2 py-1 rounded text-xs font-medium ${
                  domain.label === 'productive' ? 'bg-emerald-100 text-emerald-700' :
                  domain.label === 'unproductive' ? 'bg-rose-100 text-rose-700' :
                  'bg-slate-100 text-slate-600'
                }`}>
                  {domain.label}
                </span>
                <span className="flex-1 font-medium text-slate-800">{domain.domain}</span>
                <span className="text-sm text-slate-600">{formatTime(domain.duration_sec)}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-slate-400 text-center py-8">No browser data</p>
        )}
      </div>

      {/* Timeline */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <h3 className="text-lg font-semibold text-slate-800 mb-4">Timeline</h3>
        {timeline?.blocks?.length > 0 ? (
          <div className="space-y-2">
            {timeline.blocks.slice(0, 20).map((block, index) => (
              <div
                key={index}
                className={`flex items-center gap-4 p-3 rounded-lg ${
                  block.type === 'present' ? 'bg-emerald-50' :
                  block.type === 'absent' ? 'bg-rose-50' :
                  block.type === 'idle' ? 'bg-amber-50' :
                  'bg-slate-50'
                }`}
              >
                <span className="text-lg">
                  {block.type === 'present' ? '👤' :
                   block.type === 'absent' ? '🚫' :
                   block.type === 'idle' ? '💤' :
                   block.type === 'active' ? '💻' : '📷'}
                </span>
                <span className="flex-1 capitalize font-medium text-slate-700">
                  {block.type === 'active' && block.app_name ? `${block.type} • ${block.app_name}` : block.type}
                </span>
                <span className="text-sm text-slate-500">
                  {new Date(block.start_ts).toLocaleTimeString()} - {new Date(block.end_ts).toLocaleTimeString()}
                </span>
                <span className="text-sm font-medium text-slate-600">
                  {formatTime(block.duration_sec)}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-slate-400 text-center py-8">No timeline data</p>
        )}
      </div>
    </div>
  );
}

function StatCard({ title, value, color }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <p className="text-sm text-slate-500">{title}</p>
      <p className={`text-2xl font-bold mt-1 ${color}`}>{value}</p>
    </div>
  );
}

export default EmployeeDetail;
