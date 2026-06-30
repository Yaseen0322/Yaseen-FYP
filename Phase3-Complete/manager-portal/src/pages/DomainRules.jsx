import React, { useEffect, useState } from 'react';
import api from '../utils/api';

function DomainRules() {
  const [rules, setRules] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [formError, setFormError] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingRule, setEditingRule] = useState(null);
  const [newRule, setNewRule] = useState({
    domain: '',
    category: '',
    label: 'neutral'
  });

  useEffect(() => {
    loadRules();
  }, []);

  const loadRules = async () => {
    try {
      setError('');
      const response = await api.get('/manager/domain-rules');
      setRules(response.data);
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to load domain rules');
    } finally {
      setIsLoading(false);
    }
  };

  const resetForm = () => {
    setNewRule({ domain: '', category: '', label: 'neutral' });
    setEditingRule(null);
    setFormError('');
  };

  const openCreateModal = () => {
    resetForm();
    setShowModal(true);
  };

  const openEditModal = (rule) => {
    setEditingRule(rule);
    setNewRule({
      domain: rule.domain || '',
      category: rule.category || '',
      label: rule.label || 'neutral'
    });
    setFormError('');
    setShowModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setFormError('');
      if (editingRule) {
        await api.patch(`/manager/domain-rules/${editingRule.id}`, newRule);
      } else {
        await api.post('/manager/domain-rules', newRule);
      }
      setShowModal(false);
      resetForm();
      await loadRules();
    } catch (error) {
      setFormError(error.response?.data?.detail || 'Failed to save rule');
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this rule?')) return;
    try {
      await api.delete(`/manager/domain-rules/${id}`);
      await loadRules();
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to delete rule');
    }
  };

  const getLabelStyle = (label) => {
    switch (label) {
      case 'productive':
        return 'bg-emerald-100 text-emerald-700';
      case 'unproductive':
        return 'bg-rose-100 text-rose-700';
      default:
        return 'bg-slate-100 text-slate-600';
    }
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
          <h1 className="text-2xl font-bold text-slate-800">Domain Rules</h1>
          <p className="text-slate-500 mt-1">Classify websites as productive or unproductive</p>
        </div>
        <button
          onClick={openCreateModal}
          className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg transition-colors"
        >
          + Add Rule
        </button>
      </div>

      {error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-700 rounded-xl p-4 flex items-center justify-between">
          <span>{error}</span>
          <button
            onClick={loadRules}
            className="text-sm font-medium text-rose-700 hover:text-rose-800"
          >
            Retry
          </button>
        </div>
      )}

      {/* Default Rules Info */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
        <p className="text-blue-800 text-sm">
          <strong>Note:</strong> Common sites like GitHub, Stack Overflow are automatically classified as productive. 
          Social media sites are classified as unproductive by default. Add custom rules to override these defaults.
        </p>
      </div>

      {/* Rules Table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Domain
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Category
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Label
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {rules.length > 0 ? rules.map((rule) => (
                <tr key={rule.id} className="hover:bg-slate-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="font-medium text-slate-800">{rule.domain}</span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600">
                    {rule.category}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full capitalize ${getLabelStyle(rule.label)}`}>
                      {rule.label}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <button
                      onClick={() => openEditModal(rule)}
                      className="mr-4 text-primary-600 hover:text-primary-700 text-sm font-medium"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(rule.id)}
                      className="text-rose-600 hover:text-rose-700 text-sm font-medium"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              )) : (
                <tr>
                  <td colSpan="4" className="px-6 py-12 text-center text-slate-400">
                    No custom rules defined. Add rules to classify specific domains.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Rule Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-6 w-full max-w-md mx-4 animate-fade-in">
            <h2 className="text-xl font-bold text-slate-800 mb-6">
              {editingRule ? 'Edit Domain Rule' : 'Add Domain Rule'}
            </h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Domain</label>
                <input
                  type="text"
                  value={newRule.domain}
                  onChange={(e) => setNewRule({ ...newRule, domain: e.target.value })}
                  className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="e.g., example.com"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Category</label>
                <input
                  type="text"
                  value={newRule.category}
                  onChange={(e) => setNewRule({ ...newRule, category: e.target.value })}
                  className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="e.g., Social Media, Development"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Label</label>
                <select
                  value={newRule.label}
                  onChange={(e) => setNewRule({ ...newRule, label: e.target.value })}
                  className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="productive">Productive</option>
                  <option value="neutral">Neutral</option>
                  <option value="unproductive">Unproductive</option>
                </select>
              </div>
              {formError && (
                <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                  {formError}
                </div>
              )}
              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => {
                    setShowModal(false);
                    resetForm();
                  }}
                  className="flex-1 py-2 px-4 border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 py-2 px-4 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
                >
                  {editingRule ? 'Save Changes' : 'Add Rule'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default DomainRules;
