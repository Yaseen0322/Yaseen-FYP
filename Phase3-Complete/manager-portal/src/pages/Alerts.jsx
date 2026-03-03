import React, { useEffect, useState } from 'react';
import api from '../utils/api';

function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [alertRules, setAlertRules] = useState([]);
  const [stats, setStats] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('alerts');
  const [showRuleModal, setShowRuleModal] = useState(false);
  const [newRule, setNewRule] = useState({
    name: '',
    alert_type: 'excessive_idle',
    severity: 'medium',
    config_json: { threshold_seconds: 7200 },
    notify_manager: true
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [alertsRes, rulesRes, statsRes] = await Promise.all([
        api.get('/alerts/'),
        api.get('/alerts/rules'),
        api.get('/alerts/stats')
      ]);
      setAlerts(alertsRes.data);
      setAlertRules(rulesRes.data);
      setStats(statsRes.data);
    } catch (error) {
      console.error('Failed to load alerts:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAcknowledge = async (alertId) => {
    try {
      await api.post(`/alerts/${alertId}/acknowledge`);
      loadData();
    } catch (error) {
      console.error('Failed to acknowledge:', error);
    }
  };

  const handleCreateRule = async (e) => {
    e.preventDefault();
    try {
      await api.post('/alerts/rules', newRule);
      setShowRuleModal(false);
      setNewRule({
        name: '',
        alert_type: 'excessive_idle',
        severity: 'medium',
        config_json: { threshold_seconds: 7200 },
        notify_manager: true
      });
      loadData();
    } catch (error) {
      alert('Failed to create rule');
    }
  };

  const handleToggleRule = async (ruleId, isActive) => {
    try {
      await api.patch(`/alerts/rules/${ruleId}?is_active=${!isActive}`);
      loadData();
    } catch (error) {
      console.error('Failed to toggle rule:', error);
    }
  };

  const getSeverityStyle = (severity) => {
    switch (severity) {
      case 'high': return 'bg-rose-100 text-rose-700 border-rose-200';
      case 'medium': return 'bg-amber-100 text-amber-700 border-amber-200';
      default: return 'bg-blue-100 text-blue-700 border-blue-200';
    }
  };

  const getAlertTypeLabel = (type) => {
    const labels = {
      'excessive_idle': 'Excessive Idle',
      'camera_off_long': 'Camera Off',
      'low_productivity': 'Low Productivity',
      'absent_during_hours': 'Absent'
    };
    return labels[type] || type;
  };

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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Alerts</h1>
          <p className="text-slate-500 mt-1">Monitor and manage employee alerts</p>
        </div>
        <button
          onClick={() => setShowRuleModal(true)}
          className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg transition-colors"
        >
          + Create Rule
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <p className="text-sm text-slate-500">Total Alerts</p>
          <p className="text-2xl font-bold text-slate-800">{stats?.total || 0}</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <p className="text-sm text-slate-500">Unread</p>
          <p className="text-2xl font-bold text-rose-600">{stats?.unread || 0}</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <p className="text-sm text-slate-500">High Severity (7d)</p>
          <p className="text-2xl font-bold text-amber-600">{stats?.by_severity?.high || 0}</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <p className="text-sm text-slate-500">Active Rules</p>
          <p className="text-2xl font-bold text-emerald-600">{alertRules.filter(r => r.is_active).length}</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-4 border-b border-slate-200">
        <button
          onClick={() => setActiveTab('alerts')}
          className={`pb-3 px-1 font-medium transition-colors ${
            activeTab === 'alerts'
              ? 'text-primary-600 border-b-2 border-primary-600'
              : 'text-slate-500 hover:text-slate-700'
          }`}
        >
          Alerts ({alerts.length})
        </button>
        <button
          onClick={() => setActiveTab('rules')}
          className={`pb-3 px-1 font-medium transition-colors ${
            activeTab === 'rules'
              ? 'text-primary-600 border-b-2 border-primary-600'
              : 'text-slate-500 hover:text-slate-700'
          }`}
        >
          Rules ({alertRules.length})
        </button>
      </div>

      {/* Content */}
      {activeTab === 'alerts' ? (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          {alerts.length > 0 ? (
            <div className="divide-y divide-slate-200">
              {alerts.map((alert) => (
                <div key={alert.id} className={`p-4 ${!alert.is_read ? 'bg-blue-50/50' : ''}`}>
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-4">
                      <div className={`px-2 py-1 rounded text-xs font-medium ${getSeverityStyle(alert.severity)}`}>
                        {alert.severity}
                      </div>
                      <div>
                        <p className="font-medium text-slate-800">{alert.title}</p>
                        <p className="text-sm text-slate-500 mt-1">{alert.message}</p>
                        <div className="flex items-center gap-4 mt-2 text-xs text-slate-400">
                          <span>{getAlertTypeLabel(alert.alert_type)}</span>
                          <span>{new Date(alert.triggered_at).toLocaleString()}</span>
                        </div>
                      </div>
                    </div>
                    {!alert.is_acknowledged && (
                      <button
                        onClick={() => handleAcknowledge(alert.id)}
                        className="text-sm text-primary-600 hover:text-primary-700 font-medium"
                      >
                        Acknowledge
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="p-8 text-center text-slate-400">No alerts</p>
          )}
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          {alertRules.length > 0 ? (
            <div className="divide-y divide-slate-200">
              {alertRules.map((rule) => (
                <div key={rule.id} className="p-4 flex items-center justify-between">
                  <div>
                    <p className="font-medium text-slate-800">{rule.name}</p>
                    <div className="flex items-center gap-4 mt-1 text-sm text-slate-500">
                      <span>{getAlertTypeLabel(rule.alert_type)}</span>
                      <span className={`px-2 py-0.5 rounded text-xs ${getSeverityStyle(rule.severity)}`}>
                        {rule.severity}
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={() => handleToggleRule(rule.id, rule.is_active)}
                    className={`w-12 h-6 rounded-full transition-colors relative ${
                      rule.is_active ? 'bg-emerald-500' : 'bg-slate-300'
                    }`}
                  >
                    <div
                      className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${
                        rule.is_active ? 'translate-x-7' : 'translate-x-1'
                      }`}
                    ></div>
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <p className="p-8 text-center text-slate-400">No rules defined</p>
          )}
        </div>
      )}

      {/* Create Rule Modal */}
      {showRuleModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-6 w-full max-w-md mx-4 animate-fade-in">
            <h2 className="text-xl font-bold text-slate-800 mb-6">Create Alert Rule</h2>
            <form onSubmit={handleCreateRule} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Name</label>
                <input
                  type="text"
                  value={newRule.name}
                  onChange={(e) => setNewRule({ ...newRule, name: e.target.value })}
                  className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Alert Type</label>
                <select
                  value={newRule.alert_type}
                  onChange={(e) => setNewRule({ ...newRule, alert_type: e.target.value })}
                  className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="excessive_idle">Excessive Idle</option>
                  <option value="camera_off_long">Camera Off Too Long</option>
                  <option value="low_productivity">Low Productivity</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Severity</label>
                <select
                  value={newRule.severity}
                  onChange={(e) => setNewRule({ ...newRule, severity: e.target.value })}
                  className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </div>
              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowRuleModal(false)}
                  className="flex-1 py-2 px-4 border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 py-2 px-4 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                >
                  Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default Alerts;
