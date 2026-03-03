import React, { useEffect, useState } from 'react';
import api from '../utils/api';

function MLClassifications() {
  const [classifications, setClassifications] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState('pending');

  useEffect(() => {
    loadData();
  }, [filter]);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const response = await api.get(`/ml/classifications?status=${filter}`);
      setClassifications(response.data);
    } catch (error) {
      console.error('Failed to load classifications:', error);
      // Mock data for demonstration
      setClassifications([
        { id: 1, classification_type: 'domain', input_value: 'example.com', predicted_category: 'Other', predicted_label: 'neutral', confidence: 50, is_approved: false },
        { id: 2, classification_type: 'app', input_value: 'Custom App', predicted_category: 'Other', predicted_label: 'neutral', confidence: 45, is_approved: false },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleApprove = async (id, newLabel = null) => {
    try {
      await api.post(`/ml/classifications/${id}/approve`, { label: newLabel });
      loadData();
    } catch (error) {
      // Demo mode - just update local state
      setClassifications(prev => prev.map(c => 
        c.id === id ? { ...c, is_approved: true, predicted_label: newLabel || c.predicted_label } : c
      ));
    }
  };

  const handleReject = async (id) => {
    try {
      await api.delete(`/ml/classifications/${id}`);
      loadData();
    } catch (error) {
      // Demo mode
      setClassifications(prev => prev.filter(c => c.id !== id));
    }
  };

  const getLabelStyle = (label) => {
    switch (label) {
      case 'productive': return 'bg-emerald-100 text-emerald-700';
      case 'unproductive': return 'bg-rose-100 text-rose-700';
      default: return 'bg-slate-100 text-slate-600';
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
      <div>
        <h1 className="text-2xl font-bold text-slate-800">ML Classifications</h1>
        <p className="text-slate-500 mt-1">Review and approve AI-suggested classifications</p>
      </div>

      {/* Info Banner */}
      <div className="bg-purple-50 border border-purple-200 rounded-xl p-4">
        <div className="flex items-start gap-3">
          <span className="text-2xl">🤖</span>
          <div>
            <p className="font-medium text-purple-800">Machine Learning Classification</p>
            <p className="text-sm text-purple-600 mt-1">
              The system automatically classifies new domains and applications. 
              Review and approve classifications to improve accuracy over time.
            </p>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-2">
        {['pending', 'approved', 'all'].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filter === f
                ? 'bg-primary-100 text-primary-700'
                : 'bg-white text-slate-600 hover:bg-slate-50 border border-slate-200'
            }`}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      {/* Classifications Table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase">Type</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase">Value</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase">Category</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase">Predicted Label</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase">Confidence</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {classifications.length > 0 ? classifications.map((item) => (
                <tr key={item.id} className="hover:bg-slate-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 text-xs rounded-full ${
                      item.classification_type === 'domain' 
                        ? 'bg-blue-100 text-blue-700' 
                        : 'bg-purple-100 text-purple-700'
                    }`}>
                      {item.classification_type}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="font-medium text-slate-800">{item.input_value}</span>
                  </td>
                  <td className="px-6 py-4 text-slate-600">
                    {item.predicted_category}
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 text-xs rounded-full font-medium ${getLabelStyle(item.predicted_label)}`}>
                      {item.predicted_label}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <div className="w-20 h-2 bg-slate-100 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-primary-500 rounded-full"
                          style={{ width: `${item.confidence}%` }}
                        ></div>
                      </div>
                      <span className="text-sm text-slate-600">{item.confidence}%</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    {!item.is_approved ? (
                      <div className="flex items-center gap-2">
                        <select
                          className="text-sm border border-slate-200 rounded px-2 py-1"
                          defaultValue={item.predicted_label}
                          onChange={(e) => handleApprove(item.id, e.target.value)}
                        >
                          <option value="productive">Productive</option>
                          <option value="neutral">Neutral</option>
                          <option value="unproductive">Unproductive</option>
                        </select>
                        <button
                          onClick={() => handleApprove(item.id)}
                          className="text-emerald-600 hover:text-emerald-700 text-sm font-medium"
                        >
                          ✓
                        </button>
                        <button
                          onClick={() => handleReject(item.id)}
                          className="text-rose-600 hover:text-rose-700 text-sm font-medium"
                        >
                          ✕
                        </button>
                      </div>
                    ) : (
                      <span className="text-emerald-600 text-sm">✓ Approved</span>
                    )}
                  </td>
                </tr>
              )) : (
                <tr>
                  <td colSpan="6" className="px-6 py-12 text-center text-slate-400">
                    No classifications to review
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default MLClassifications;
