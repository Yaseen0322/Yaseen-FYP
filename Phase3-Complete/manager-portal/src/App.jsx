import React, { Suspense, lazy, useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './stores/authStore';
import ErrorBoundary from './components/ErrorBoundary';

const Layout = lazy(() => import('./components/Layout'));
const Login = lazy(() => import('./pages/Login'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Employees = lazy(() => import('./pages/Employees'));
const EmployeeDetail = lazy(() => import('./pages/EmployeeDetail'));
const DomainRules = lazy(() => import('./pages/DomainRules'));
const Departments = lazy(() => import('./pages/Departments'));
const Alerts = lazy(() => import('./pages/Alerts'));
const DepartmentAnalytics = lazy(() => import('./pages/DepartmentAnalytics'));
const Integrations = lazy(() => import('./pages/Integrations'));
const MLClassifications = lazy(() => import('./pages/MLClassifications'));

function RouteFallback() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="text-center">
        <div className="w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
        <p className="text-slate-500">Loading page...</p>
      </div>
    </div>
  );
}

function App() {
  const { isLoggedIn, checkAuth, isLoading } = useAuthStore();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-slate-500">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <Suspense fallback={<RouteFallback />}>
        <Routes>
          <Route path="/login" element={
            isLoggedIn ? <Navigate to="/" replace /> : <Login />
          } />
          
          <Route path="/" element={
            isLoggedIn ? <Layout /> : <Navigate to="/login" replace />
          }>
            <Route index element={<Dashboard />} />
            <Route path="employees" element={<Employees />} />
            <Route path="employees/:id" element={<EmployeeDetail />} />
            <Route path="domain-rules" element={<DomainRules />} />
            <Route path="departments" element={<Departments />} />
            <Route path="alerts" element={<Alerts />} />
            <Route path="department-analytics" element={<DepartmentAnalytics />} />
            <Route path="integrations" element={<Integrations />} />
            <Route path="ml-classifications" element={<MLClassifications />} />
          </Route>
        </Routes>
      </Suspense>
    </ErrorBoundary>
  );
}

export default App;
