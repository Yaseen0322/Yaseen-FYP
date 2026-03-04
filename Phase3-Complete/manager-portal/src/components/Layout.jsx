import React from 'react';
import { Outlet, NavLink } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';

const navItems = [
  { path: '/', label: 'Dashboard', icon: '📊' },
  { path: '/employees', label: 'Employees', icon: '👥' },
  { path: '/departments', label: 'Departments', icon: '🏢' },
  { path: '/analytics', label: 'Analytics', icon: '📈' },
  { path: '/alerts', label: 'Alerts', icon: '🚨' },
  { path: '/domain-rules', label: 'Domain Rules', icon: '🌐' },
  { path: '/integrations', label: 'Integrations', icon: '🔗' },
  { path: '/ml-classifications', label: 'ML Classifications', icon: '🤖' },
];

function Layout() {
  const { user, logout } = useAuthStore();

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Top Navigation */}
      <nav className="bg-white border-b border-slate-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            {/* Logo */}
            <div className="flex items-center">
              <span className="text-2xl mr-2">📊</span>
              <span className="font-semibold text-lg text-slate-800">Manager Portal</span>
            </div>

            {/* Nav Links */}
            <div className="flex items-center gap-1 overflow-x-auto py-2">
              {navItems.map((item) => (
                <NavLink
                  key={item.path}
                  to={item.path}
                  end={item.path === '/'}
                  className={({ isActive }) =>
                    `px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-primary-50 text-primary-700'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                    }`
                  }
                >
                  <span className="mr-2">{item.icon}</span>
                  {item.label}
                </NavLink>
              ))}
            </div>

            {/* User Menu */}
            <div className="flex items-center gap-4">
              <div className="text-right">
                <p className="text-sm font-medium text-slate-700">{user?.name}</p>
                <p className="text-xs text-slate-500">{user?.role}</p>
              </div>
              <button
                onClick={logout}
                className="px-3 py-1.5 text-sm text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors"
              >
                Sign Out
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
    </div>
  );
}

export default Layout;
