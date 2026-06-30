import React, { useEffect, useState } from 'react';
import api from '../utils/api';

function Departments() {
  const [departments, setDepartments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [formError, setFormError] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingDept, setEditingDept] = useState(null);
  const [newDept, setNewDept] = useState({
    name: '',
    description: ''
  });

  useEffect(() => {
    loadDepartments();
  }, []);

  const loadDepartments = async () => {
    try {
      setError('');
      const response = await api.get('/org/departments');
      setDepartments(response.data);
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to load departments');
    } finally {
      setIsLoading(false);
    }
  };

  const resetForm = () => {
    setNewDept({ name: '', description: '' });
    setEditingDept(null);
    setFormError('');
  };

  const openCreateModal = () => {
    resetForm();
    setShowModal(true);
  };

  const openEditModal = (department) => {
    setEditingDept(department);
    setNewDept({
      name: department.name || '',
      description: department.description || ''
    });
    setFormError('');
    setShowModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setFormError('');
      if (editingDept) {
        await api.patch(`/org/departments/${editingDept.id}`, newDept);
      } else {
        await api.post('/org/departments', newDept);
      }
      setShowModal(false);
      resetForm();
      await loadDepartments();
    } catch (error) {
      setFormError(error.response?.data?.detail || 'Failed to save department');
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this department?')) return;
    try {
      await api.delete(`/org/departments/${id}`);
      await loadDepartments();
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to delete department');
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
          <h1 className="text-2xl font-bold text-slate-800">Departments</h1>
          <p className="text-slate-500 mt-1">Organize employees into departments</p>
        </div>
        <button
          onClick={openCreateModal}
          className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg transition-colors"
        >
          + Add Department
        </button>
      </div>

      {error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-700 rounded-xl p-4 flex items-center justify-between">
          <span>{error}</span>
          <button
            onClick={loadDepartments}
            className="text-sm font-medium text-rose-700 hover:text-rose-800"
          >
            Retry
          </button>
        </div>
      )}

      {/* Departments Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {departments.length > 0 ? departments.map((dept) => (
          <div key={dept.id} className="bg-white rounded-xl border border-slate-200 p-6">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-lg font-semibold text-slate-800">{dept.name}</h3>
                <p className="text-slate-500 text-sm mt-1">{dept.description || 'No description'}</p>
              </div>
              <div className="w-10 h-10 rounded-xl bg-primary-100 flex items-center justify-center text-xl">
                🏢
              </div>
            </div>
            <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between">
              <span className="text-sm text-slate-500">
                Created {new Date(dept.created_at).toLocaleDateString()}
              </span>
              <button
                onClick={() => openEditModal(dept)}
                className="text-sm text-primary-600 hover:text-primary-700 font-medium"
              >
                Edit
              </button>
              <button
                onClick={() => handleDelete(dept.id)}
                className="text-sm text-rose-600 hover:text-rose-700 font-medium"
              >
                Delete
              </button>
            </div>
          </div>
        )) : (
          <div className="col-span-full bg-white rounded-xl border border-slate-200 p-12 text-center">
            <span className="text-5xl">🏢</span>
            <p className="text-slate-500 mt-4">No departments yet. Create one to get started.</p>
          </div>
        )}
      </div>

      {/* Add Department Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-6 w-full max-w-md mx-4 animate-fade-in">
            <h2 className="text-xl font-bold text-slate-800 mb-6">
              {editingDept ? 'Edit Department' : 'Add Department'}
            </h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Name</label>
                <input
                  type="text"
                  value={newDept.name}
                  onChange={(e) => setNewDept({ ...newDept, name: e.target.value })}
                  className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="e.g., Engineering"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
                <textarea
                  value={newDept.description}
                  onChange={(e) => setNewDept({ ...newDept, description: e.target.value })}
                  className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="Optional description..."
                  rows={3}
                />
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
                  {editingDept ? 'Save Changes' : 'Add Department'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default Departments;
