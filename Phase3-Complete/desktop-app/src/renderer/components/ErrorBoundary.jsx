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
    console.error('Desktop renderer error:', error, info);
  }

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="card max-w-md w-full p-6">
          <h1 className="text-lg font-semibold text-white">Dashboard could not load</h1>
          <p className="text-sm text-white/60 mt-2">
            Restart the employee app or sign in again. Tracking data remains stored locally.
          </p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="mt-5 px-4 py-2 rounded-lg bg-white/10 text-white text-sm font-medium hover:bg-white/20"
          >
            Reload
          </button>
        </div>
      </div>
    );
  }
}

export default ErrorBoundary;
