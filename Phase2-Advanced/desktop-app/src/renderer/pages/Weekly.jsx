import React, { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts';

function Weekly() {
  const [weekOffset, setWeekOffset] = useState(0);
  const [weeklyData, setWeeklyData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadWeeklyData();
  }, [weekOffset]);

  const loadWeeklyData = async () => {
    setIsLoading(true);
    try {
      const data = await window.electronAPI.getWeekly(weekOffset);
      setWeeklyData(data);
    } catch (error) {
      console.error('Failed to load weekly data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const formatTime = (seconds) => {
    if (!seconds) return '0h';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  const formatHours = (seconds) => {
    return (seconds / 3600).toFixed(1);
  };

  const getDayName = (dateStr) => {
    return new Date(dateStr).toLocaleDateString('en-US', { weekday: 'short' });
  };

  const chartData = weeklyData?.daily_summaries?.map(day => ({
    name: getDayName(day.date),
    focus: parseFloat(formatHours(day.focus_sec)),
    idle: parseFloat(formatHours(day.idle_sec)),
    present: parseFloat(formatHours(day.present_sec)),
  })) || [];

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
          <h1 className="text-3xl font-display font-bold text-white">Weekly Report</h1>
          <p className="text-white/40 mt-1">
            {weeklyData?.week_start} - {weeklyData?.week_end}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setWeekOffset(weekOffset - 1)}
            className="px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white transition-colors"
          >
            ← Previous
          </button>
          <button
            onClick={() => setWeekOffset(0)}
            disabled={weekOffset === 0}
            className="px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white transition-colors disabled:opacity-50"
          >
            This Week
          </button>
          <button
            onClick={() => setWeekOffset(weekOffset + 1)}
            disabled={weekOffset >= 0}
            className="px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white transition-colors disabled:opacity-50"
          >
            Next →
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card p-6 bg-gradient-to-br from-emerald-500/10 to-teal-500/10">
          <p className="text-white/60 text-sm">Total Focus Time</p>
          <p className="text-3xl font-bold text-white mt-2">
            {formatTime(weeklyData?.total_focus_sec)}
          </p>
          <p className="text-emerald-400 text-sm mt-2">
            Avg: {formatTime(Math.round(weeklyData?.avg_daily_focus_sec || 0))}/day
          </p>
        </div>

        <div className="card p-6 bg-gradient-to-br from-amber-500/10 to-orange-500/10">
          <p className="text-white/60 text-sm">Total Idle Time</p>
          <p className="text-3xl font-bold text-white mt-2">
            {formatTime(weeklyData?.total_idle_sec)}
          </p>
        </div>

        <div className="card p-6 bg-gradient-to-br from-blue-500/10 to-indigo-500/10">
          <p className="text-white/60 text-sm">Total Present Time</p>
          <p className="text-3xl font-bold text-white mt-2">
            {formatTime(weeklyData?.total_present_sec)}
          </p>
          <p className="text-blue-400 text-sm mt-2">
            Avg: {formatTime(Math.round(weeklyData?.avg_daily_present_sec || 0))}/day
          </p>
        </div>
      </div>

      {/* Chart */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-white mb-6">Daily Activity</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData}>
            <XAxis dataKey="name" stroke="#666" />
            <YAxis stroke="#666" label={{ value: 'Hours', angle: -90, position: 'insideLeft', fill: '#666' }} />
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '12px',
                color: '#fff'
              }}
              formatter={(value) => [`${value}h`, '']}
            />
            <Bar dataKey="focus" name="Focus" fill="#10b981" radius={[4, 4, 0, 0]} />
            <Bar dataKey="present" name="Present" fill="#6366f1" radius={[4, 4, 0, 0]} />
            <Bar dataKey="idle" name="Idle" fill="#f59e0b" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
        <div className="flex justify-center gap-6 mt-4">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded bg-emerald-500"></div>
            <span className="text-sm text-white/60">Focus</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded bg-indigo-500"></div>
            <span className="text-sm text-white/60">Present</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded bg-amber-500"></div>
            <span className="text-sm text-white/60">Idle</span>
          </div>
        </div>
      </div>

      {/* Daily Breakdown */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Daily Breakdown</h3>
        <div className="space-y-4">
          {weeklyData?.daily_summaries?.map((day, index) => (
            <div
              key={index}
              className="flex items-center gap-4 p-4 rounded-xl bg-white/5 hover:bg-white/10 transition-colors"
            >
              <div className="w-16 text-center">
                <p className="text-lg font-bold text-white">{getDayName(day.date)}</p>
                <p className="text-xs text-white/40">{day.date}</p>
              </div>
              <div className="flex-1 grid grid-cols-3 gap-4">
                <div>
                  <p className="text-xs text-white/40">Focus</p>
                  <p className="text-white font-medium">{formatTime(day.focus_sec)}</p>
                </div>
                <div>
                  <p className="text-xs text-white/40">Present</p>
                  <p className="text-white font-medium">{formatTime(day.present_sec)}</p>
                </div>
                <div>
                  <p className="text-xs text-white/40">Idle</p>
                  <p className="text-white font-medium">{formatTime(day.idle_sec)}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default Weekly;
