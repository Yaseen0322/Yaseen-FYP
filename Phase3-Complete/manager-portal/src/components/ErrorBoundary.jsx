import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    console.error('Manager portal render error:', error, info);
  }

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
        <div className="max-w-md w-full bg-white border border-slate-200 rounded-lg p-6 shadow-sm">
          <h1 className="text-lg font-semibold text-slate-900">Dashboard could not load</h1>
          <p className="text-sm text-slate-600 mt-2">
            Refresh the page or sign in again. If this keeps happening, check the backend service logs.
          </p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="mt-5 px-4 py-2 rounded-md bg-primary-600 text-white text-sm font-medium hover:bg-primary-700"
          >
            Reload
          </button>
        </div>
      </div>
    );
  }
}

export default ErrorBoundary;
