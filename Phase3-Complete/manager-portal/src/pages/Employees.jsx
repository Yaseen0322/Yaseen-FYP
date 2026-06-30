import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../utils/api';
import { useAuthStore } from '../stores/authStore';
import PaginationControls from '../components/PaginationControls';

function Employees() {
  const { user } = useAuthStore();
  const canCreateManagers = ['admin', 'super_admin'].includes(user?.role);
  const canManageTeam = ['admin', 'super_admin'].includes(user?.role);
  const [employees, setEmployees] = useState([]);
  const [totalEmployees, setTotalEmployees] = useState(0);
  const [departments, setDepartments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [feedback, setFeedback] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [modalError, setModalError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [limit] = useState(10);
  const [offset, setOffset] = useState(0);
  const [newEmployee, setNewEmployee] = useState({
    name: '',
    email: '',
    password: '',
    employee_id: '',
    dept_id: null,
    role: 'employee'
  });

  useEffect(() => {
    loadData();
  }, [offset]);

  const loadData = async () => {
    try {
      setError('');
      const [employeesRes, deptsRes] = await Promise.all([
        api.get('/users/', { params: { limit, offset } }),
        api.get('/org/departments')
      ]);
      setEmployees(employeesRes.data.items);
      setTotalEmployees(employeesRes.data.total);
      setDepartments(deptsRes.data);
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to load team members');
    } finally {
      setIsLoading(false);
    }
  };

  const resetForm = () => {
    setNewEmployee({
      name: '',
      email: '',
      password: '',
      employee_id: '',
      dept_id: null,
      role: 'employee'
    });
    setModalError('');
  };

  const handleCreateEmployee = async (e) => {
    e.preventDefault();
    if (newEmployee.password.length < 8) {
      setModalError('Password must be at least 8 characters long.');
      return;
    }

    try {
      setIsSubmitting(true);
      setModalError('');
      await api.post('/users/', newEmployee);
      setShowModal(false);
      resetForm();
      setFeedback('Team member created.');
      await loadData();
    } catch (error) {
      setModalError(error.response?.data?.detail || 'Failed to create team member');
    } finally {
      setIsSubmitting(false);
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
          <h1 className="text-2xl font-bold text-slate-800">
            {canManageTeam ? 'Team Members' : 'Employees'}
          </h1>
          <p className="text-slate-500 mt-1">
            {canManageTeam ? 'Manage employees and managers in your organization' : 'Manage your team members'}
          </p>
        </div>
        <button
          onClick={() => {
            resetForm();
            setShowModal(true);
          }}
          className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg transition-colors"
        >
          {canManageTeam ? '+ Add Team Member' : '+ Add Employee'}
        </button>
      </div>

      {feedback && !error && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          {feedback}
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        {error && (
          <div className="border-b border-rose-200 bg-rose-50 px-6 py-4 text-sm text-rose-700">
            <div className="flex items-center justify-between gap-4">
              <span>{error}</span>
              <button
                onClick={loadData}
                className="font-medium text-rose-700 hover:text-rose-800"
              >
                Retry
              </button>
            </div>
          </div>
        )}
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Employee
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Employee ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Department
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Role
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {employees.map((employee) => (
                <tr key={employee.id} className="hover:bg-slate-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center text-primary-600 font-medium">
                        {employee.name?.charAt(0) || 'U'}
                      </div>
                      <div className="ml-4">
                        <div className="text-sm font-medium text-slate-900">{employee.name}</div>
                        <div className="text-sm text-slate-500">{employee.email}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600">
                    {employee.employee_id || '—'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600">
                    {departments.find(d => d.id === employee.dept_id)?.name || '—'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm text-slate-600 capitalize">{employee.role}</span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                      employee.is_active
                        ? 'bg-emerald-100 text-emerald-700'
                        : 'bg-slate-100 text-slate-600'
                    }`}>
                      {employee.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <Link
                      to={`/employees/${employee.id}`}
                      className="text-primary-600 hover:text-primary-700 text-sm font-medium"
                    >
                      View Report
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!error && employees.length === 0 && (
          <div className="px-6 py-12 text-center text-slate-400">
            No team members found for this page.
          </div>
        )}
        <PaginationControls
          total={totalEmployees}
          limit={limit}
          offset={offset}
          label="team members"
          onPageChange={setOffset}
        />
      </div>

      {/* Add Employee Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-6 w-full max-w-md mx-4 animate-fade-in">
            <h2 className="text-xl font-bold text-slate-800 mb-6">
              {canManageTeam ? 'Add Team Member' : 'Add New Employee'}
            </h2>
            <form onSubmit={handleCreateEmployee} className="space-y-4">
              {modalError && (
                <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                  {modalError}
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Name</label>
                <input
                  type="text"
                  value={newEmployee.name}
                  onChange={(e) => setNewEmployee({ ...newEmployee, name: e.target.value })}
                  className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
                <input
                  type="email"
                  value={newEmployee.email}
                  onChange={(e) => setNewEmployee({ ...newEmployee, email: e.target.value })}
                  className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Password</label>
                <input
                  type="password"
                  value={newEmployee.password}
                  onChange={(e) => setNewEmployee({ ...newEmployee, password: e.target.value })}
                  className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Employee ID</label>
                <input
                  type="text"
                  value={newEmployee.employee_id}
                  onChange={(e) => setNewEmployee({ ...newEmployee, employee_id: e.target.value })}
                  className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Department</label>
                <select
                  value={newEmployee.dept_id || ''}
                  onChange={(e) => setNewEmployee({ ...newEmployee, dept_id: e.target.value ? parseInt(e.target.value) : null })}
                  className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="">Select Department</option>
                  {departments.map(dept => (
                    <option key={dept.id} value={dept.id}>{dept.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Role</label>
                <select
                  value={newEmployee.role}
                  onChange={(e) => setNewEmployee({ ...newEmployee, role: e.target.value })}
                  className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="employee">Employee</option>
                  {canCreateManagers && <option value="manager">Manager</option>}
                </select>
              </div>
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
                  disabled={isSubmitting}
                  className="flex-1 py-2 px-4 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
                >
                  {isSubmitting ? 'Saving...' : canManageTeam ? 'Add Team Member' : 'Add Employee'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default Employees;
