'use client';
import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({
      error,
      errorInfo
    });
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <div className="error-container">
            <div className="error-icon">⚠️</div>
            <h2>Something went wrong</h2>
            <p className="error-message">
              {this.props.fallbackMessage || 'An unexpected error occurred. Please try refreshing the page.'}
            </p>
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <details className="error-details">
                <summary>Error details</summary>
                <pre>{this.state.error.toString()}</pre>
                <pre>{this.state.errorInfo?.componentStack}</pre>
              </details>
            )}
            <div className="error-actions">
              <button onClick={this.handleReset} className="reset-btn">
                Try Again
              </button>
              <button onClick={() => window.location.reload()} className="refresh-btn">
                Refresh Page
              </button>
            </div>
          </div>

          <style jsx>{`
            .error-boundary {
              position: fixed;
              top: 0;
              left: 0;
              right: 0;
              bottom: 0;
              display: flex;
              align-items: center;
              justify-content: center;
              background: rgba(255, 255, 255, 0.95);
              z-index: 10000;
              padding: 20px;
            }

            .error-container {
              max-width: 500px;
              background: white;
              border-radius: 16px;
              padding: 32px;
              box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
              text-align: center;
            }

            .error-icon {
              font-size: 3rem;
              margin-bottom: 16px;
            }

            h2 {
              color: var(--deep-blue);
              margin-bottom: 12px;
              font-size: 1.5rem;
            }

            .error-message {
              color: #666;
              margin-bottom: 24px;
              line-height: 1.5;
            }

            .error-details {
              background: #f5f5f5;
              border-radius: 8px;
              padding: 12px;
              margin-bottom: 20px;
              text-align: left;
              max-height: 200px;
              overflow-y: auto;
            }

            .error-details summary {
              cursor: pointer;
              color: #999;
              font-size: 0.85rem;
              margin-bottom: 8px;
            }

            .error-details pre {
              font-size: 0.75rem;
              color: #666;
              white-space: pre-wrap;
              word-break: break-word;
              margin: 4px 0;
            }

            .error-actions {
              display: flex;
              gap: 12px;
              justify-content: center;
            }

            button {
              padding: 10px 20px;
              border-radius: 8px;
              font-weight: 600;
              cursor: pointer;
              transition: all 0.2s ease;
              border: none;
            }

            .reset-btn {
              background: var(--primary-teal);
              color: white;
            }

            .reset-btn:hover {
              background: var(--gold);
            }

            .refresh-btn {
              background: transparent;
              color: var(--primary-teal);
              border: 2px solid var(--primary-teal);
            }

            .refresh-btn:hover {
              background: var(--cream);
            }
          `}</style>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;