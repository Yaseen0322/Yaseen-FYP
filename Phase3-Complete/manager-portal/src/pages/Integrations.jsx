import React, { useEffect, useState } from 'react';
import api from '../utils/api';
import { useAuthStore } from '../stores/authStore';

function Integrations() {
  const { user } = useAuthStore();
  const isAdmin = ['admin', 'super_admin'].includes(user?.role);
  const [integrations, setIntegrations] = useState([]);
  const [ssoProviders, setSsoProviders] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('integrations');
  const [showModal, setShowModal] = useState(false);
  const [modalType, setModalType] = useState('integration');
  const [formData, setFormData] = useState({
    name: '',
    integration_type: 'slack',
    provider_type: 'google',
    config_json: {}
  });

  useEffect(() => {
    if (!isAdmin) {
      setIsLoading(false);
      return;
    }
    loadData();
  }, [isAdmin]);

  const loadData = async () => {
    setError(null);
    try {
      const [integrationsRes, ssoRes] = await Promise.all([
        api.get('/integrations/'),
        api.get('/integrations/sso')
      ]);
      setIntegrations(integrationsRes.data);
      setSsoProviders(ssoRes.data);
    } catch (error) {
      console.error('Failed to load integrations:', error);
      setError(error.response?.data?.detail || 'Failed to load integrations');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      if (modalType === 'integration') {
        await api.post('/integrations/', {
          integration_type: formData.integration_type,
          name: formData.name,
          config_json: formData.config_json
        });
      } else {
        await api.post('/integrations/sso', {
          provider_type: formData.provider_type,
          name: formData.name,
          config_json: formData.config_json
        });
      }
      setShowModal(false);
      setFormData({ name: '', integration_type: 'slack', provider_type: 'google', config_json: {} });
      loadData();
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to create');
    }
  };

  const handleToggle = async (id, type) => {
    try {
      if (type === 'integration') {
        await api.post(`/integrations/${id}/toggle`);
      } else {
        await api.post(`/integrations/sso/${id}/toggle`);
      }
      loadData();
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to toggle');
    }
  };

  const handleTest = async (id) => {
    try {
      const response = await api.post(`/integrations/${id}/test`);
      alert(response.data.success ? 'Connection successful!' : `Test failed: ${response.data.message}`);
      loadData();
    } catch (error) {
      alert('Test failed');
    }
  };

  const getIntegrationIcon = (type) => {
    const icons = {
      'slack': '💬',
      'jira': '📋',
      'microsoft_teams': '👥',
      'google_workspace': '📧'
    };
    return icons[type] || '🔗';
  };

  const getSSOIcon = (type) => {
    const icons = {
      'google': '🔵',
      'microsoft': '🟦',
      'okta': '🟠'
    };
    return icons[type] || '🔐';
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-10 h-10 border-4 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!isAdmin) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-8">
        <h1 className="text-2xl font-bold text-slate-800">Integrations</h1>
        <p className="text-slate-600 mt-2">
          You need an admin account to manage integrations and SSO providers.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Integrations</h1>
          <p className="text-slate-500 mt-1">Connect with Slack, Jira, and SSO providers</p>
        </div>
        <button
          onClick={() => { setModalType(activeTab === 'sso' ? 'sso' : 'integration'); setShowModal(true); }}
          className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg transition-colors"
        >
          + Add {activeTab === 'sso' ? 'SSO Provider' : 'Integration'}
        </button>
      </div>

      {error && (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 text-rose-700">
          {error}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-4 border-b border-slate-200">
        <button
          onClick={() => setActiveTab('integrations')}
          className={`pb-3 px-1 font-medium transition-colors ${
            activeTab === 'integrations'
              ? 'text-primary-600 border-b-2 border-primary-600'
              : 'text-slate-500 hover:text-slate-700'
          }`}
        >
          Integrations ({integrations.length})
        </button>
        <button
          onClick={() => setActiveTab('sso')}
          className={`pb-3 px-1 font-medium transition-colors ${
            activeTab === 'sso'
              ? 'text-primary-600 border-b-2 border-primary-600'
              : 'text-slate-500 hover:text-slate-700'
          }`}
        >
          SSO Providers ({ssoProviders.length})
        </button>
      </div>

      {/* Content */}
      {activeTab === 'integrations' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {integrations.length > 0 ? integrations.map((integration) => (
            <div key={integration.id} className="bg-white rounded-xl border border-slate-200 p-6">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-3xl">{getIntegrationIcon(integration.integration_type)}</span>
                  <div>
                    <h3 className="font-semibold text-slate-800">{integration.name}</h3>
                    <p className="text-sm text-slate-500 capitalize">{integration.integration_type.replace('_', ' ')}</p>
                  </div>
                </div>
                <span className={`px-2 py-1 text-xs rounded-full ${
                  integration.is_active
                    ? 'bg-emerald-100 text-emerald-700'
                    : 'bg-slate-100 text-slate-600'
                }`}>
                  {integration.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
              
              <div className="mt-4 pt-4 border-t border-slate-100">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-500">
                    {integration.is_configured ? '✓ Configured' : '⚠ Not configured'}
                  </span>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleTest(integration.id)}
                      className="text-primary-600 hover:text-primary-700"
                    >
                      Test
                    </button>
                    <button
                      onClick={() => handleToggle(integration.id, 'integration')}
                      className={integration.is_active ? 'text-amber-600' : 'text-emerald-600'}
                    >
                      {integration.is_active ? 'Disable' : 'Enable'}
                    </button>
                  </div>
                </div>
                {integration.last_error && (
                  <p className="text-xs text-rose-500 mt-2">{integration.last_error}</p>
                )}
              </div>
            </div>
          )) : (
            <div className="col-span-full bg-white rounded-xl border border-slate-200 p-12 text-center">
              <span className="text-5xl">🔗</span>
              <p className="text-slate-500 mt-4">No integrations configured yet</p>
            </div>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {ssoProviders.length > 0 ? ssoProviders.map((provider) => (
            <div key={provider.id} className="bg-white rounded-xl border border-slate-200 p-6">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-3xl">{getSSOIcon(provider.provider_type)}</span>
                  <div>
                    <h3 className="font-semibold text-slate-800">{provider.name}</h3>
                    <p className="text-sm text-slate-500 capitalize">{provider.provider_type}</p>
                  </div>
                </div>
                <span className={`px-2 py-1 text-xs rounded-full ${
                  provider.is_active
                    ? 'bg-emerald-100 text-emerald-700'
                    : 'bg-slate-100 text-slate-600'
                }`}>
                  {provider.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
              
              <div className="mt-4 pt-4 border-t border-slate-100 flex justify-end">
                <button
                  onClick={() => handleToggle(provider.id, 'sso')}
                  className={`text-sm ${provider.is_active ? 'text-amber-600' : 'text-emerald-600'}`}
                >
                  {provider.is_active ? 'Disable' : 'Enable'}
                </button>
              </div>
            </div>
          )) : (
            <div className="col-span-full bg-white rounded-xl border border-slate-200 p-12 text-center">
              <span className="text-5xl">🔐</span>
              <p className="text-slate-500 mt-4">No SSO providers configured yet</p>
            </div>
          )}
        </div>
      )}

      {/* Create Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-6 w-full max-w-md mx-4 animate-fade-in">
            <h2 className="text-xl font-bold text-slate-800 mb-6">
              Add {modalType === 'integration' ? 'Integration' : 'SSO Provider'}
            </h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  required
                />
              </div>
              
              {modalType === 'integration' ? (
                <>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Type</label>
                    <select
                      value={formData.integration_type}
                      onChange={(e) => setFormData({ ...formData, integration_type: e.target.value })}
                      className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                    >
                      <option value="slack">Slack</option>
                      <option value="jira">Jira</option>
                      <option value="microsoft_teams">Microsoft Teams</option>
                    </select>
                  </div>
                  
                  {formData.integration_type === 'slack' && (
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">Webhook URL</label>
                      <input
                        type="url"
                        placeholder="https://hooks.slack.com/services/..."
                        onChange={(e) => setFormData({ ...formData, config_json: { webhook_url: e.target.value } })}
                        className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                      />
                    </div>
                  )}
                  
                  {formData.integration_type === 'jira' && (
                    <>
                      <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">Jira API URL</label>
                        <input
                          type="url"
                          placeholder="https://your-domain.atlassian.net"
                          onChange={(e) => setFormData({ 
                            ...formData, 
                            config_json: { ...formData.config_json, api_url: e.target.value } 
                          })}
                          className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
                        <input
                          type="email"
                          onChange={(e) => setFormData({ 
                            ...formData, 
                            config_json: { ...formData.config_json, email: e.target.value } 
                          })}
                          className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">API Token</label>
                        <input
                          type="password"
                          onChange={(e) => setFormData({ 
                            ...formData, 
                            config_json: { ...formData.config_json, api_token: e.target.value } 
                          })}
                          className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                        />
                      </div>
                    </>
                  )}
                </>
              ) : (
                <>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Provider</label>
                    <select
                      value={formData.provider_type}
                      onChange={(e) => setFormData({ ...formData, provider_type: e.target.value })}
                      className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                    >
                      <option value="google">Google</option>
                      <option value="microsoft">Microsoft</option>
                      <option value="okta">Okta</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Client ID</label>
                    <input
                      type="text"
                      onChange={(e) => setFormData({ 
                        ...formData, 
                        config_json: { ...formData.config_json, client_id: e.target.value } 
                      })}
                      className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Client Secret</label>
                    <input
                      type="password"
                      onChange={(e) => setFormData({ 
                        ...formData, 
                        config_json: { ...formData.config_json, client_secret: e.target.value } 
                      })}
                      className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                  </div>
                </>
              )}
              
              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
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

export default Integrations;
