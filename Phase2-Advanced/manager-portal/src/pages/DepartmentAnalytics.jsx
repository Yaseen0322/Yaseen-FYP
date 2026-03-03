import React, { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line } from 'recharts';
import api from '../utils/api';

function DepartmentAnalytics() {
  const [departmentsSummary, setDepartmentsSummary] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [trends, setTrends] = useState(null);
  const [selectedDept, setSelectedDept] = useState(null);
  const [deptDetails, setDeptDetails] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [comparisonMetric, setComparisonMetric] = useState('focus');

  useEffect(() => {
    loadData();
  }, [comparisonMetric]);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [summaryRes, comparisonRes, trendsRes] = await Promise.all([
        api.get('/analytics/departments/summary'),
        api.get(`/analytics/departments/comparison?metric=${comparisonMetric}`),
        api.get('/analytics/trends/weekly')
      ]);
      setDepartmentsSummary(summaryRes.data);
      setComparison(comparisonRes.data);
      setTrends(trendsRes.data);
    } catch (error) {
      console.error('Failed to load analytics:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadDeptDetails = async (deptId) => {
    try {
      const response = await api.get(`/analytics/departments/${deptId}/details`);
      setDeptDetails(response.data);
      setSelectedDept(deptId);
    } catch (error) {
      console.error('Failed to load department details:', error);
    }
  };

  const formatTime = (seconds) => {
    if (!seconds) return '0h';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-10 h-10 border-4 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Department Analytics</h1>
        <p className="text-slate-500 mt-1">Compare and analyze department performance</p>
      </div>

      {/* Department Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {departmentsSummary?.departments?.map((dept, index) => (
          <div
            key={dept.department.id}
            onClick={() => loadDeptDetails(dept.department.id)}
            className="bg-white rounded-xl border border-slate-200 p-6 cursor-pointer hover:border-primary-300 hover:shadow-md transition-all"
          >
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-semibold text-slate-800">{dept.department.name}</h3>
                <p className="text-sm text-slate-500">{dept.employee_count} employees</p>
              </div>
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center text-white text-lg"
                style={{ backgroundColor: COLORS[index % COLORS.length] }}
              >
                🏢
              </div>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-slate-400">Avg Focus</p>
                <p className="text-lg font-semibold text-slate-700">{formatTime(dept.avg_focus_sec)}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400">Productivity</p>
                <p className="text-lg font-semibold text-emerald-600">{dept.productivity_ratio}%</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Comparison Chart */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-slate-800">Department Comparison</h3>
          <select
            value={comparisonMetric}
            onChange={(e) => setComparisonMetric(e.target.value)}
            className="px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="focus">Focus Time</option>
            <option value="presence">Presence Time</option>
            <option value="productivity">Productivity %</option>
          </select>
        </div>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={comparison?.comparison}>
            <XAxis dataKey="department" />
            <YAxis />
            <Tooltip
              formatter={(value) => [
                comparisonMetric === 'productivity' ? `${value}%` : formatTime(value),
                comparisonMetric.charAt(0).toUpperCase() + comparisonMetric.slice(1)
              ]}
            />
            <Bar dataKey="value" fill="#6366f1" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Weekly Trends */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <h3 className="text-lg font-semibold text-slate-800 mb-6">Weekly Trends</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={trends?.trends}>
            <XAxis dataKey="day" />
            <YAxis />
            <Tooltip
              formatter={(value, name) => [formatTime(value), name === 'avg_focus_sec' ? 'Avg Focus' : 'Avg Present']}
            />
            <Line type="monotone" dataKey="avg_focus_sec" stroke="#6366f1" strokeWidth={2} name="avg_focus_sec" />
            <Line type="monotone" dataKey="avg_present_sec" stroke="#10b981" strokeWidth={2} name="avg_present_sec" />
          </LineChart>
        </ResponsiveContainer>
        <div className="flex justify-center gap-6 mt-4">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded bg-primary-500"></div>
            <span className="text-sm text-slate-600">Avg Focus Time</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded bg-emerald-500"></div>
            <span className="text-sm text-slate-600">Avg Present Time</span>
          </div>
        </div>
      </div>

      {/* Department Details Modal */}
      {selectedDept && deptDetails && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl p-6 w-full max-w-4xl max-h-[80vh] overflow-auto animate-fade-in">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-slate-800">{deptDetails.department.name} - Details</h2>
              <button
                onClick={() => { setSelectedDept(null); setDeptDetails(null); }}
                className="text-slate-400 hover:text-slate-600"
              >
                ✕
              </button>
            </div>

            {/* Employee Stats */}
            <div className="mb-6">
              <h3 className="font-semibold text-slate-700 mb-4">Employee Performance</h3>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Employee</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Focus</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Present</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Idle</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Productive</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {deptDetails.employees.map((emp) => (
                      <tr key={emp.id}>
                        <td className="px-4 py-3">
                          <p className="font-medium text-slate-800">{emp.name}</p>
                          <p className="text-xs text-slate-500">{emp.email}</p>
                        </td>
                        <td className="px-4 py-3 text-sm text-slate-600">{formatTime(emp.focus_sec)}</td>
                        <td className="px-4 py-3 text-sm text-slate-600">{formatTime(emp.present_sec)}</td>
                        <td className="px-4 py-3 text-sm text-slate-600">{formatTime(emp.idle_sec)}</td>
                        <td className="px-4 py-3 text-sm text-emerald-600">{formatTime(emp.productive_sec)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Top Apps */}
            <div>
              <h3 className="font-semibold text-slate-700 mb-4">Top Applications</h3>
              <div className="grid grid-cols-2 gap-3">
                {deptDetails.top_apps.slice(0, 6).map((app, index) => (
                  <div key={index} className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
                    <span className="text-xl">💻</span>
                    <div className="flex-1">
                      <p className="font-medium text-slate-700">{app.app_name}</p>
                    </div>
                    <span className="text-sm text-slate-500">{formatTime(app.duration_sec)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default DepartmentAnalytics;
