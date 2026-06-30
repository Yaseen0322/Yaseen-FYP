import React, { useEffect, useState } from 'react';
import api from '../utils/api';
import { useAuthStore } from '../stores/authStore';
import PaginationControls from '../components/PaginationControls';

const emptyFormState = {
  name: '',
  integration_type: 'slack',
  provider_type: 'google',
  config_json: {},
};

function Integrations() {
  const { user } = useAuthStore();
  const isAdmin = ['admin', 'super_admin'].includes(user?.role);
  const [integrations, setIntegrations] = useState([]);
  const [integrationsTotal, setIntegrationsTotal] = useState(0);
  const [ssoProviders, setSsoProviders] = useState([]);
  const [ssoTotal, setSsoTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [feedback, setFeedback] = useState('');
  const [activeTab, setActiveTab] = useState('integrations');
  const [showModal, setShowModal] = useState(false);
  const [modalType, setModalType] = useState('integration');
  const [editingId, setEditingId] = useState(null);
  const [modalError, setModalError] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [integrationOffset, setIntegrationOffset] = useState(0);
  const [ssoOffset, setSsoOffset] = useState(0);
  const [pageLimit] = useState(6);
  const [formData, setFormData] = useState(emptyFormState);

  useEffect(() => {
    if (!isAdmin) {
      setIsLoading(false);
      return;
    }
    loadData();
  }, [isAdmin, integrationOffset, ssoOffset]);

  const resetForm = () => {
    setFormData(emptyFormState);
    setEditingId(null);
    setModalError('');
  };

  const loadData = async () => {
    setError(null);
    try {
      const [integrationsRes, ssoRes] = await Promise.all([
        api.get('/integrations/', { params: { limit: pageLimit, offset: integrationOffset } }),
        api.get('/integrations/sso', { params: { limit: pageLimit, offset: ssoOffset } }),
      ]);
      setIntegrations(integrationsRes.data.items);
      setIntegrationsTotal(integrationsRes.data.total);
      setSsoProviders(ssoRes.data.items);
      setSsoTotal(ssoRes.data.total);
    } catch (loadError) {
      console.error('Failed to load integrations:', loadError);
      setError(loadError.response?.data?.detail || 'Failed to load integrations');
    } finally {
      setIsLoading(false);
    }
  };

  const openCreateModal = (type) => {
    resetForm();
    setModalType(type);
    setShowModal(true);
  };

  const openEditModal = async (type, id) => {
    setFeedback('');
    setModalError('');
    setModalType(type);
    setShowModal(true);
    setEditingId(id);
    setIsSaving(true);

    try {
      const endpoint = type === 'integration' ? `/integrations/${id}` : `/integrations/sso/${id}`;
      const response = await api.get(endpoint);
      const payload = response.data;
      setFormData({
        name: payload.name,
        integration_type: payload.integration_type || 'slack',
        provider_type: payload.provider_type || 'google',
        config_json: payload.config_json || {},
      });
    } catch (loadError) {
      console.error('Failed to load configuration:', loadError);
      setModalError(loadError.response?.data?.detail || 'Failed to load configuration');
    } finally {
      setIsSaving(false);
    }
  };

  const validateForm = () => {
    if (!formData.name.trim()) {
      return 'Name is required.';
    }

    if (modalType === 'integration') {
      if (formData.integration_type === 'slack' && !formData.config_json.webhook_url?.trim()) {
        return 'Slack webhook URL is required.';
      }
      if (formData.integration_type === 'jira') {
        if (!formData.config_json.api_url?.trim()) {
          return 'Jira API URL is required.';
        }
        if (!formData.config_json.email?.trim()) {
          return 'Jira email is required.';
        }
        if (!formData.config_json.api_token?.trim()) {
          return 'Jira API token is required.';
        }
      }
    } else {
      if (!formData.config_json.client_id?.trim()) {
        return 'Client ID is required.';
      }
      if (!formData.config_json.client_secret?.trim()) {
        return 'Client secret is required.';
      }
      if (!formData.config_json.redirect_uri?.trim()) {
        return 'Redirect URI is required.';
      }
      if (formData.provider_type === 'microsoft' && !formData.config_json.tenant_id?.trim()) {
        return 'Tenant ID is required for Microsoft SSO.';
      }
    }

    return '';
  };

  const handleSave = async (e) => {
    e.preventDefault();
    const validationError = validateForm();
    if (validationError) {
      setModalError(validationError);
      return;
    }

    setIsSaving(true);
    setModalError('');
    setFeedback('');

    try {
      if (modalType === 'integration') {
        const payload = {
          integration_type: formData.integration_type,
          name: formData.name.trim(),
          config_json: formData.config_json,
        };
        if (editingId) {
          await api.patch(`/integrations/${editingId}`, {
            name: payload.name,
            config_json: payload.config_json,
          });
          setFeedback('Integration updated.');
        } else {
          await api.post('/integrations/', payload);
          setFeedback('Integration created.');
        }
      } else {
        const payload = {
          provider_type: formData.provider_type,
          name: formData.name.trim(),
          config_json: formData.config_json,
        };
        if (editingId) {
          await api.patch(`/integrations/sso/${editingId}`, {
            name: payload.name,
            config_json: payload.config_json,
          });
          setFeedback('SSO provider updated.');
        } else {
          await api.post('/integrations/sso', payload);
          setFeedback('SSO provider created.');
        }
      }

      setShowModal(false);
      resetForm();
      await loadData();
    } catch (saveError) {
      console.error('Failed to save integration settings:', saveError);
      setModalError(saveError.response?.data?.detail || 'Failed to save changes');
    } finally {
      setIsSaving(false);
    }
  };

  const handleToggle = async (id, type) => {
    setFeedback('');
    setError(null);
    try {
      if (type === 'integration') {
        await api.post(`/integrations/${id}/toggle`);
        setFeedback('Integration state updated.');
      } else {
        await api.post(`/integrations/sso/${id}/toggle`);
        setFeedback('SSO provider state updated.');
      }
      await loadData();
    } catch (toggleError) {
      console.error('Failed to toggle integration state:', toggleError);
      setError(toggleError.response?.data?.detail || 'Failed to update status');
    }
  };

  const handleDelete = async (id, type) => {
    if (!window.confirm(`Delete this ${type === 'integration' ? 'integration' : 'SSO provider'}?`)) {
      return;
    }

    setFeedback('');
    setError(null);
    try {
      if (type === 'integration') {
        await api.delete(`/integrations/${id}`);
        setFeedback('Integration deleted.');
      } else {
        await api.delete(`/integrations/sso/${id}`);
        setFeedback('SSO provider deleted.');
      }
      await loadData();
    } catch (deleteError) {
      console.error('Failed to delete integration config:', deleteError);
      setError(deleteError.response?.data?.detail || 'Failed to delete item');
    }
  };

  const handleTest = async (id) => {
    setFeedback('');
    setError(null);
    try {
      const response = await api.post(`/integrations/${id}/test`);
      if (response.data.success) {
        setFeedback('Connection test succeeded.');
      } else {
        setError(response.data.message || 'Connection test failed');
      }
      await loadData();
    } catch (testError) {
      console.error('Failed to test integration:', testError);
      setError(testError.response?.data?.detail || 'Connection test failed');
    }
  };

  const getIntegrationIcon = (type) => {
    const icons = {
      slack: 'SL',
      jira: 'JI',
    };
    return icons[type] || 'IN';
  };

  const getSSOIcon = (type) => {
    const icons = {
      google: 'GO',
      microsoft: 'MS',
      okta: 'OK',
    };
    return icons[type] || 'SS';
  };

  const updateConfigValue = (key, value) => {
    setFormData((current) => ({
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Integrations</h1>
          <p className="text-slate-500 mt-1">
            Configure Slack alert delivery, Jira connectivity checks, and SSO providers.
          </p>
        </div>
        <button
          onClick={() => openCreateModal(activeTab === 'sso' ? 'sso' : 'integration')}
          className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg transition-colors"
        >
          + Add {activeTab === 'sso' ? 'SSO Provider' : 'Integration'}
        </button>
      </div>

      <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        <p className="font-semibold">Operational notes</p>
        <p className="mt-2">
          Slack alert delivery runs when the background worker is running: <code>python -m app.workers.operational_jobs --interval 300</code>.
        </p>
        <p className="mt-1">
          Jira in this release supports configuration and connectivity tests only. Automatic issue sync and worklog export are not enabled.
        </p>
      </div>

      {error && (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 text-rose-700">
          <div className="flex items-center justify-between gap-4">
            <span>{error}</span>
            <button onClick={loadData} className="font-medium text-rose-700 hover:text-rose-800">
              Retry
            </button>
          </div>
        </div>
      )}

      {feedback && !error && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 text-emerald-700">
          {feedback}
        </div>
      )}

      <div className="flex gap-4 border-b border-slate-200">
        <button
          onClick={() => setActiveTab('integrations')}
          className={`pb-3 px-1 font-medium transition-colors ${
            activeTab === 'integrations'
              ? 'text-primary-600 border-b-2 border-primary-600'
              : 'text-slate-500 hover:text-slate-700'
          }`}
        >
          Integrations ({integrationsTotal})
        </button>
        <button
          onClick={() => setActiveTab('sso')}
          className={`pb-3 px-1 font-medium transition-colors ${
            activeTab === 'sso'
              ? 'text-primary-600 border-b-2 border-primary-600'
              : 'text-slate-500 hover:text-slate-700'
          }`}
        >
          SSO Providers ({ssoTotal})
        </button>
      </div>

      {activeTab === 'integrations' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {integrations.length > 0 ? integrations.map((integration) => (
            <div key={integration.id} className="bg-white rounded-xl border border-slate-200 p-6">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-3">
                  <span className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-slate-100 font-semibold text-slate-700">
                    {getIntegrationIcon(integration.integration_type)}
                  </span>
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

              <p className="mt-4 text-sm text-slate-500">
                {integration.integration_type === 'slack'
                  ? 'Sends newly generated alerts to Slack when the worker is running.'
                  : 'Stores Jira credentials and validates connectivity. Automatic sync is disabled in this release.'}
              </p>

              <div className="mt-4 pt-4 border-t border-slate-100 space-y-3">
                <div className="text-sm text-slate-500">
                  {integration.is_configured ? 'Configured' : 'Configuration missing'}
                </div>
                {integration.last_error && (
                  <p className="text-xs text-rose-500">{integration.last_error}</p>
                )}
                <div className="flex flex-wrap gap-3 text-sm">
                  <button onClick={() => openEditModal('integration', integration.id)} className="text-primary-600 hover:text-primary-700">
                    Edit
                  </button>
                  <button onClick={() => handleTest(integration.id)} className="text-slate-700 hover:text-slate-900">
                    Test
                  </button>
                  <button
                    onClick={() => handleToggle(integration.id, 'integration')}
                    className={integration.is_active ? 'text-amber-600' : 'text-emerald-600'}
                  >
                    {integration.is_active ? 'Disable' : 'Enable'}
                  </button>
                  <button onClick={() => handleDelete(integration.id, 'integration')} className="text-rose-600 hover:text-rose-700">
                    Delete
                  </button>
                </div>
              </div>
            </div>
          )) : (
            <div className="col-span-full bg-white rounded-xl border border-slate-200 p-12 text-center">
              <span className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-100 text-slate-700 font-semibold">
                IN
              </span>
              <p className="text-slate-500 mt-4">No integrations configured yet.</p>
            </div>
          )}
          <div className="col-span-full">
            <PaginationControls
              total={integrationsTotal}
              limit={pageLimit}
              offset={integrationOffset}
              label="integrations"
              onPageChange={setIntegrationOffset}
            />
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {ssoProviders.length > 0 ? ssoProviders.map((provider) => (
            <div key={provider.id} className="bg-white rounded-xl border border-slate-200 p-6">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-3">
                  <span className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-slate-100 font-semibold text-slate-700">
                    {getSSOIcon(provider.provider_type)}
                  </span>
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

              <p className="mt-4 text-sm text-slate-500">
                Secure OAuth sign-in is supported for configured providers with an allowlisted redirect URI.
              </p>

              <div className="mt-4 pt-4 border-t border-slate-100 flex flex-wrap gap-3 text-sm">
                <button onClick={() => openEditModal('sso', provider.id)} className="text-primary-600 hover:text-primary-700">
                  Edit
                </button>
                <button
                  onClick={() => handleToggle(provider.id, 'sso')}
                  className={provider.is_active ? 'text-amber-600' : 'text-emerald-600'}
                >
                  {provider.is_active ? 'Disable' : 'Enable'}
                </button>
                <button onClick={() => handleDelete(provider.id, 'sso')} className="text-rose-600 hover:text-rose-700">
                  Delete
                </button>
              </div>
            </div>
          )) : (
            <div className="col-span-full bg-white rounded-xl border border-slate-200 p-12 text-center">
              <span className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-100 text-slate-700 font-semibold">
                SS
              </span>
              <p className="text-slate-500 mt-4">No SSO providers configured yet.</p>
            </div>
          )}
          <div className="col-span-full">
            <PaginationControls
              total={ssoTotal}
              limit={pageLimit}
              offset={ssoOffset}
              label="providers"
              onPageChange={setSsoOffset}
            />
          </div>
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl p-6 w-full max-w-md animate-fade-in">
            <h2 className="text-xl font-bold text-slate-800 mb-2">
              {editingId ? 'Edit' : 'Add'} {modalType === 'integration' ? 'Integration' : 'SSO Provider'}
            </h2>
            <p className="text-sm text-slate-500 mb-6">
              {modalType === 'integration'
                ? 'Slack supports live alert delivery through the worker. Jira is limited to configuration and connectivity validation.'
                : 'Enter the provider credentials and redirect URI that match your OAuth application setup.'}
            </p>

            <form onSubmit={handleSave} className="space-y-4">
              {modalError && (
                <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                  {modalError}
                </div>
              )}

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
                      onChange={(e) => setFormData({ ...formData, integration_type: e.target.value, config_json: {} })}
                      className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                      disabled={Boolean(editingId)}
                    >
                      <option value="slack">Slack</option>
                      <option value="jira">Jira</option>
                    </select>
                  </div>

                  {formData.integration_type === 'slack' && (
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">Webhook URL</label>
                      <input
                        type="url"
                        value={formData.config_json.webhook_url || ''}
                        placeholder="https://hooks.slack.com/services/..."
                        onChange={(e) => updateConfigValue('webhook_url', e.target.value)}
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
                          value={formData.config_json.api_url || ''}
                          placeholder="https://your-domain.atlassian.net"
                          onChange={(e) => updateConfigValue('api_url', e.target.value)}
                          className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
                        <input
                          type="email"
                          value={formData.config_json.email || ''}
                          onChange={(e) => updateConfigValue('email', e.target.value)}
                          className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">API Token</label>
                        <input
                          type="password"
                          value={formData.config_json.api_token || ''}
                          onChange={(e) => updateConfigValue('api_token', e.target.value)}
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
                      onChange={(e) => setFormData({ ...formData, provider_type: e.target.value, config_json: {} })}
                      className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                      disabled={Boolean(editingId)}
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
                      value={formData.config_json.client_id || ''}
                      onChange={(e) => updateConfigValue('client_id', e.target.value)}
                      className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Client Secret</label>
                    <input
                      type="password"
                      value={formData.config_json.client_secret || ''}
                      onChange={(e) => updateConfigValue('client_secret', e.target.value)}
                      className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Redirect URI</label>
                    <input
                      type="url"
                      value={formData.config_json.redirect_uri || ''}
                      placeholder="https://portal.example.com/auth/callback"
                      onChange={(e) => updateConfigValue('redirect_uri', e.target.value)}
                      className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Allowed Email Domain</label>
                    <input
                      type="text"
                      value={formData.config_json.domain || ''}
                      placeholder="company.com"
                      onChange={(e) => updateConfigValue('domain', e.target.value)}
                      className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                  </div>
                  {formData.provider_type === 'microsoft' && (
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">Tenant ID</label>
                      <input
                        type="text"
                        value={formData.config_json.tenant_id || ''}
                        placeholder="common or tenant-id"
                        onChange={(e) => updateConfigValue('tenant_id', e.target.value)}
                        className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                      />
                    </div>
                  )}
                </>
              )}

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => {
                    setShowModal(false);
                    resetForm();
                  }}
                  className="flex-1 py-2 px-4 border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSaving}
                  className="flex-1 py-2 px-4 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-60"
                >
                  {isSaving ? 'Saving...' : editingId ? 'Save Changes' : 'Create'}
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
