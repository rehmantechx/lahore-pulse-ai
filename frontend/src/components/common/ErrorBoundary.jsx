/**
 * ErrorBoundary — React error boundary for graceful failure handling.
 *
 * Catches JavaScript errors in child component tree.
 * Shows a user-friendly error message with retry option.
 * Prevents the entire application from crashing.
 */

import { Component } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    // Log to console for debugging — never fabricate an AI result
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      const { fallbackTitle, fallbackMessage } = this.props;
      return (
        <div className="error-boundary" role="alert">
          <div className="error-boundary__icon">
            <AlertTriangle size={24} aria-hidden="true" />
          </div>
          <h3 className="error-boundary__title">
            {fallbackTitle || 'Something went wrong'}
          </h3>
          <p className="error-boundary__message">
            {fallbackMessage || 'An unexpected error occurred. The rest of the application continues to work.'}
          </p>
          <button
            className="error-boundary__retry"
            onClick={this.handleRetry}
            type="button"
          >
            <RefreshCw size={14} aria-hidden="true" /> Try Again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
