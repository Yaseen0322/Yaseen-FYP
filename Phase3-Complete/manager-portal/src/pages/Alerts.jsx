import React, { useEffect, useState } from 'react';
import api from '../utils/api';
import PaginationControls from '../components/PaginationControls';

const defaultRule = {
  name: '',
  alert_type: 'excessive_idle',
  severity: 'medium',
  config_json: { threshold_seconds: 7200 },
  notify_employee: false,
  notify_manager: true,
};

function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [alertsTotal, setAlertsTotal] = useState(0);
  const [alertRules, setAlertRules] = useState([]);
  const [stats, setStats] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [feedback, setFeedback] = useState('');
  const [activeTab, setActiveTab] = useState('alerts');
  const [showRuleModal, setShowRuleModal] = useState(false);
  const [ruleModalError, setRuleModalError] = useState('');
  const [editingRuleId, setEditingRuleId] = useState(null);
  const [isSubmittingRule, setIsSubmittingRule] = useState(false);
  const [isProcessingRules, setIsProcessingRules] = useState(false);
  const [alertsOffset, setAlertsOffset] = useState(0);
  const [alertsLimit] = useState(10);
  const [newRule, setNewRule] = useState(defaultRule);

  useEffect(() => {
    loadData();
  }, [alertsOffset]);

  const loadData = async () => {
    try {
      setError('');
      const [alertsRes, rulesRes, statsRes] = await Promise.all([
        api.get('/alerts/', { params: { limit: alertsLimit, offset: alertsOffset } }),
        api.get('/alerts/rules'),
        api.get('/alerts/stats'),
      ]);
      setAlerts(alertsRes.data.items);
      setAlertsTotal(alertsRes.data.total);
      setAlertRules(rulesRes.data);
      setStats(statsRes.data);
    } catch (loadError) {
      console.error('Failed to load alerts:', loadError);
      setError(loadError.response?.data?.detail || 'Failed to load alerts');
    } finally {
      setIsLoading(false);
    }
  };

  const resetRuleForm = () => {
    setNewRule(defaultRule);
    setEditingRuleId(null);
    setRuleModalError('');
  };

  const getDefaultConfig = (alertType) => {
    switch (alertType) {
      case 'camera_off_long':
        return { threshold_seconds: 3600 };
      case 'low_productivity':
        return { threshold_percent: 30, min_browser_time_sec: 1800 };
      default:
        return { threshold_seconds: 7200 };
    }
  };

  const openCreateRuleModal = () => {
    resetRuleForm();
    setShowRuleModal(true);
  };

  const openEditRuleModal = (rule) => {
    setEditingRuleId(rule.id);
    setRuleModalError('');
    setNewRule({
      name: rule.name,
      alert_type: rule.alert_type,
      severity: rule.severity,
      config_json: rule.config_json || getDefaultConfig(rule.alert_type),
      notify_employee: rule.notify_employee,
      notify_manager: rule.notify_manager,
    });
    setShowRuleModal(true);
  };

  const validateRule = () => {
    if (!newRule.name.trim()) {
      return 'Rule name is required.';
    }
    if (newRule.alert_type === 'low_productivity') {
      if (!Number.isFinite(Number(newRule.config_json.threshold_percent))) {
        return 'Productivity threshold must be a number.';
      }
      if (!Number.isFinite(Number(newRule.config_json.min_browser_time_sec))) {
        return 'Minimum browser time must be a number.';
      }
      return '';
    }
    if (!Number.isFinite(Number(newRule.config_json.threshold_seconds))) {
      return 'Threshold seconds must be a number.';
    }
    return '';
  };

  const handleAcknowledge = async (alertId) => {
    try {
      setFeedback('');
      setError('');
      await api.post(`/alerts/${alertId}/acknowledge`);
      setFeedback('Alert acknowledged.');
      await loadData();
    } catch (ackError) {
      console.error('Failed to acknowledge alert:', ackError);
      setError(ackError.response?.data?.detail || 'Failed to acknowledge alert');
    }
  };

  const handleCreateOrUpdateRule = async (e) => {
    e.preventDefault();
    const validationError = validateRule();
    if (validationError) {
      setRuleModalError(validationError);
      return;
    }

    try {
      setIsSubmittingRule(true);
      setRuleModalError('');
      const payload = {
        name: newRule.name.trim(),
        alert_type: newRule.alert_type,
        severity: newRule.severity,
        config_json: newRule.config_json,
        notify_employee: newRule.notify_employee,
        notify_manager: newRule.notify_manager,
      };

      if (editingRuleId) {
        await api.patch(`/alerts/rules/${editingRuleId}`, payload);
        setFeedback('Alert rule updated.');
      } else {
        await api.post('/alerts/rules', payload);
        setFeedback('Alert rule created.');
      }

      setShowRuleModal(false);
      resetRuleForm();
      await loadData();
    } catch (saveError) {
      console.error('Failed to save rule:', saveError);
      setRuleModalError(saveError.response?.data?.detail || 'Failed to save rule');
    } finally {
      setIsSubmittingRule(false);
    }
  };

  const handleToggleRule = async (ruleId, isActive) => {
    try {
      setFeedback('');
      setError('');
      await api.patch(`/alerts/rules/${ruleId}`, {}, { params: { is_active: !isActive } });
      setFeedback('Rule state updated.');
      await loadData();
    } catch (toggleError) {
      console.error('Failed to toggle rule:', toggleError);
      setError(toggleError.response?.data?.detail || 'Failed to update rule state');
    }
  };

  const handleDeleteRule = async (ruleId) => {
    if (!window.confirm('Delete this alert rule?')) {
      return;
    }

    try {
      setFeedback('');
      setError('');
      await api.delete(`/alerts/rules/${ruleId}`);
      setFeedback('Alert rule deleted.');
      await loadData();
    } catch (deleteError) {
      console.error('Failed to delete rule:', deleteError);
      setError(deleteError.response?.data?.detail || 'Failed to delete rule');
    }
  };

  const handleProcessRules = async () => {
    try {
      setIsProcessingRules(true);
      setError('');
      setFeedback('');
      const response = await api.post('/alerts/process');
      setFeedback(
        `Alert rules processed. Created ${response.data.created_count} alert(s); sent ${response.data.slack_sent} Slack notification(s).`,
      );
      await loadData();
    } catch (processError) {
      console.error('Failed to process rules:', processError);
      setError(processError.response?.data?.detail || 'Failed to process alert rules');
    } finally {
      setIsProcessingRules(false);
    }
  };

  const getSeverityStyle = (severity) => {
    switch (severity) {
      case 'high':
        return 'bg-rose-100 text-rose-700 border-rose-200';
      case 'medium':
        return 'bg-amber-100 text-amber-700 border-amber-200';
      default:
        return 'bg-blue-100 text-blue-700 border-blue-200';
    }
  };

  const getAlertTypeLabel = (type) => {
    const labels = {
      excessive_idle: 'Excessive Idle',
      camera_off_long: 'Camera Off',
      low_productivity: 'Low Productivity',
      absent_during_hours: 'Absent',
    };
    return labels[type] || type;
  };

  const updateRuleConfig = (key, value) => {
    setNewRule((current) => ({
      ...current,
      config_json: {
        ...current.config_json,
        [key]: value,
      },
    }));
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
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Alerts</h1>
          <p className="text-slate-500 mt-1">
            Monitor alerts, adjust rules, and trigger a processing run when needed.
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={handleProcessRules}
            disabled={isProcessingRules}
            className="px-4 py-2 border border-slate-300 text-slate-700 font-medium rounded-lg hover:bg-slate-50 disabled:opacity-60"
          >
            {isProcessingRules ? 'Processing...' : 'Run Rules Now'}
          </button>
          <button
            onClick={openCreateRuleModal}
            className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg transition-colors"
          >
            + Create Rule
          </button>
        </div>
      </div>

      <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
        Alert generation is operational through the manual run button and the background worker:
        {' '}
        <code>python -m app.workers.operational_jobs --interval 300</code>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          <div className="flex items-center justify-between gap-4">
            <span>{error}</span>
            <button onClick={loadData} className="font-medium text-rose-700 hover:text-rose-800">
              Retry
            </button>
          </div>
        </div>
      )}

      {feedback && !error && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          {feedback}
        </div>
      )}

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
          <p className="text-2xl font-bold text-emerald-600">{alertRules.filter((rule) => rule.is_active).length}</p>
        </div>
      </div>

      <div className="flex gap-4 border-b border-slate-200">
        <button
          onClick={() => setActiveTab('alerts')}
          className={`pb-3 px-1 font-medium transition-colors ${
            activeTab === 'alerts'
              ? 'text-primary-600 border-b-2 border-primary-600'
              : 'text-slate-500 hover:text-slate-700'
          }`}
        >
          Alerts ({alertsTotal})
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

      {activeTab === 'alerts' ? (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          {alerts.length > 0 ? (
            <div className="divide-y divide-slate-200">
              {alerts.map((alert) => (
                <div key={alert.id} className={`p-4 ${!alert.is_read ? 'bg-blue-50/50' : ''}`}>
                  <div className="flex items-start justify-between gap-4">
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
            <p className="p-8 text-center text-slate-400">No alerts yet. Run the rules after new activity data arrives.</p>
          )}
          <PaginationControls
            total={alertsTotal}
            limit={alertsLimit}
            offset={alertsOffset}
            label="alerts"
            onPageChange={setAlertsOffset}
          />
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          {alertRules.length > 0 ? (
            <div className="divide-y divide-slate-200">
              {alertRules.map((rule) => (
                <div key={rule.id} className="p-4 flex items-center justify-between gap-4">
                  <div>
                    <p className="font-medium text-slate-800">{rule.name}</p>
                    <div className="flex items-center gap-4 mt-1 text-sm text-slate-500">
                      <span>{getAlertTypeLabel(rule.alert_type)}</span>
                      <span className={`px-2 py-0.5 rounded text-xs ${getSeverityStyle(rule.severity)}`}>
                        {rule.severity}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <button onClick={() => openEditRuleModal(rule)} className="text-primary-600 hover:text-primary-700 text-sm font-medium">
                      Edit
                    </button>
                    <button onClick={() => handleDeleteRule(rule.id)} className="text-rose-600 hover:text-rose-700 text-sm font-medium">
                      Delete
                    </button>
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
                </div>
              ))}
            </div>
          ) : (
            <p className="p-8 text-center text-slate-400">No rules defined yet.</p>
          )}
        </div>
      )}

      {showRuleModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl p-6 w-full max-w-md animate-fade-in">
            <h2 className="text-xl font-bold text-slate-800 mb-6">
              {editingRuleId ? 'Edit Alert Rule' : 'Create Alert Rule'}
            </h2>
            <form onSubmit={handleCreateOrUpdateRule} className="space-y-4">
              {ruleModalError && (
                <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                  {ruleModalError}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Rule Name</label>
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
                  onChange={(e) => setNewRule({
                    ...newRule,
                    alert_type: e.target.value,
                    config_json: getDefaultConfig(e.target.value),
                  })}
                  className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  disabled={Boolean(editingRuleId)}
                >
                  <option value="excessive_idle">Excessive Idle</option>
                  <option value="camera_off_long">Camera Off</option>
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

              {newRule.alert_type === 'low_productivity' ? (
                <>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Productivity Threshold (%)</label>
                    <input
                      type="number"
                      min="1"
                      max="100"
                      value={newRule.config_json.threshold_percent || ''}
                      onChange={(e) => updateRuleConfig('threshold_percent', Number(e.target.value))}
                      className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Minimum Browser Time (seconds)</label>
                    <input
                      type="number"
                      min="1"
                      value={newRule.config_json.min_browser_time_sec || ''}
                      onChange={(e) => updateRuleConfig('min_browser_time_sec', Number(e.target.value))}
                      className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                  </div>
                </>
              ) : (
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Threshold (seconds)</label>
                  <input
                    type="number"
                    min="1"
                    value={newRule.config_json.threshold_seconds || ''}
                    onChange={(e) => updateRuleConfig('threshold_seconds', Number(e.target.value))}
                    className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              )}

              <div className="grid grid-cols-2 gap-4 text-sm text-slate-600">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={newRule.notify_manager}
                    onChange={(e) => setNewRule({ ...newRule, notify_manager: e.target.checked })}
                  />
                  Notify managers
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={newRule.notify_employee}
                    onChange={(e) => setNewRule({ ...newRule, notify_employee: e.target.checked })}
                  />
                  Notify employee
                </label>
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => {
                    setShowRuleModal(false);
                    resetRuleForm();
                  }}
                  className="flex-1 py-2 px-4 border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingRule}
                  className="flex-1 py-2 px-4 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-60"
                >
                  {isSubmittingRule ? 'Saving...' : editingRuleId ? 'Save Changes' : 'Create Rule'}
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
